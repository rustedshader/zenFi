import statistics
from typing import Any, Dict, List, Optional, Union
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pdfplumber
from pdfplumber.page import Page
from pdfplumber.table import TableFinder
from io import BytesIO
from tqdm import tqdm
import re

# --- Constants for Configuration ---
# For extract_text_custom (if used)
CUSTOM_TEXT_Y_TOLERANCE = 1.5  # Tolerance for characters to be on the same line
CUSTOM_TEXT_MARGIN = 30  # Page margin to ignore (top/bottom)
CUSTOM_TEXT_SPACE_THRESHOLD_MULTIPLIER = (
    1.5  # Multiplier for median space to insert a space
)

# For extract_document_metadata
RE_DATE = r"\b\d{1,2}[/-]\d{1,2}[/-](?:\d{2,4})\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s\d{1,2},?\s\d{4}\b"  # Added more date patterns
RE_PHONE = r"\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"  # Improved phone regex
RE_CURRENCY = r"([\$£€¥₹])\s*\d+(?:[.,]\d+)*|\d+(?:[.,]\d+)*\s*([\$£€¥₹])"  # Improved currency regex (₹ added)
RE_HEADER_CANDIDATE = (
    r"^\s*([A-Z][A-Za-z\s]{2,}[A-ZZa-z0-9])\s*$"  # More specific header candidate
)

# For clean_and_normalize_text
RE_PAGE_NUMBER_GENERIC = r"\bPage\s*\d+\s*(?:of\s*\d+)?\b"
RE_LINE_ONLY_DIGITS = r"^\s*\d+\s*$"
RE_INVALID_CHARS_CLEANUP = r"[^\w\s\.\,\!\?\:\;\-\(\)\[\]\$\%\@\#\&\*\+\=\/\<\>\|\~]"  # Slightly more permissive, adjust as needed

# For calculate_content_quality
QUALITY_MIN_CONTENT_LENGTH = 10
QUALITY_AVG_WORD_LEN_TARGET = 6.0
QUALITY_AVG_SENT_LEN_TARGET = 15.0
QUALITY_SPECIAL_CHAR_REGEX_CONTENT = (
    RE_INVALID_CHARS_CLEANUP  # Using the same as cleaner for consistency in definition
)
QUALITY_WEIGHT_WORD_LEN = 0.25
QUALITY_WEIGHT_SENT_LEN = 0.25
QUALITY_WEIGHT_CLEANLINESS = 0.2
QUALITY_WEIGHT_STRUCTURE = 0.3

# For IntelligentTextSplitter
TEXT_SPLITTER_MIN_CHUNK_LENGTH = 50


def convert_table_to_markdown(table_data: List[List[Optional[str]]]) -> str:
    """
    Converts a list of lists representing a table into a Markdown formatted string.
    Filters out rows that are entirely empty or None.
    """
    if not table_data:
        return ""

    # Filter out rows where all cells are None or empty strings
    cleaned_table_data = []
    for row in table_data:
        if any(cell is not None and str(cell).strip() for cell in row):
            cleaned_table_data.append(row)

    if not cleaned_table_data:
        return ""

    table_lines = []
    num_cols = len(
        cleaned_table_data[0]
    )  # Assume consistent number of columns based on first valid row

    for row_idx, row in enumerate(cleaned_table_data):
        cleaned_row_cells = []
        for cell in row:
            cell_str = str(cell).replace("\n", " ").strip() if cell is not None else ""
            cleaned_row_cells.append(cell_str)
        table_lines.append("| " + " | ".join(cleaned_row_cells) + " |")

        if row_idx == 0 and len(cleaned_table_data) > 1:  # Add header separator
            separator = "| " + " | ".join(["---"] * num_cols) + " |"
            table_lines.append(separator)

    return "\n".join(table_lines)


def extract_text_from_page_custom(page: Page) -> str:
    """
    Custom text extraction from a PDF page by processing individual characters.
    NOTE: This is a complex heuristic approach. For general purposes,
    `page.extract_text(x_tolerance=3, y_tolerance=3, layout=False)` or
    `page.extract_text(layout=True)` from pdfplumber is often more robust and recommended.
    This implementation attempts a top-to-bottom, left-to-right text reconstruction.
    """
    if not page.chars:
        return ""

    # Sort characters: primarily by top coordinate (y0), secondarily by left coordinate (x0)
    # This aims for a natural reading order.
    sorted_chars = sorted(page.chars, key=lambda c: (c["y0"], c["x0"]))

    lines = []
    current_line_chars = []
    if not sorted_chars:
        return ""

    # Group characters into lines based on vertical proximity
    current_line_chars.append(sorted_chars[0])
    for char_idx in range(1, len(sorted_chars)):
        char = sorted_chars[char_idx]
        prev_char_in_line = current_line_chars[-1]

        # Check if character is on the same line (within y-tolerance)
        # and handle cases like subscripts/superscripts by checking against char_idx-1 y0 as well
        if (
            abs(char["y0"] - prev_char_in_line["y0"]) < CUSTOM_TEXT_Y_TOLERANCE
            or abs(char["bottom"] - prev_char_in_line["bottom"])
            < CUSTOM_TEXT_Y_TOLERANCE
        ):
            current_line_chars.append(char)
        else:
            # New line detected
            if current_line_chars:  # Ensure it's not empty
                # Sort characters within the detected line by their horizontal position
                current_line_chars.sort(key=lambda c: c["x0"])
                lines.append(current_line_chars)
            current_line_chars = [char]

    # Add the last accumulated line
    if current_line_chars:
        current_line_chars.sort(key=lambda c: c["x0"])
        lines.append(current_line_chars)

    # Filter lines based on page margins (using y0 of the first char in the line)
    page_height = page.height
    filtered_lines = [
        line
        for line in lines
        if line
        and CUSTOM_TEXT_MARGIN < line[0]["y0"] < page_height - CUSTOM_TEXT_MARGIN
    ]
    if not filtered_lines:
        return ""

    # Reconstruct text from lines, inferring spaces
    page_text = []
    for line_chars in filtered_lines:
        if not line_chars:
            continue

        line_text = line_chars[0]["text"]
        if len(line_chars) > 1:
            # Calculate spaces between characters
            spaces_on_line = [
                line_chars[i + 1]["x0"] - line_chars[i]["x1"]
                for i in range(len(line_chars) - 1)
            ]

            # Determine a dynamic space threshold for this line
            # (e.g., based on median character spacing on that line)
            # This helps distinguish actual spaces from tight kerning.
            median_space_on_line = (
                statistics.median(spaces_on_line) if spaces_on_line else 0
            )
            # A small positive base threshold for when median_space is 0 or very small.
            space_insertion_threshold = (
                median_space_on_line * CUSTOM_TEXT_SPACE_THRESHOLD_MULTIPLIER
                if median_space_on_line > 0.1
                else 1.0
            )

            for i in range(len(spaces_on_line)):
                if spaces_on_line[i] > space_insertion_threshold:
                    line_text += " "  # Insert a space
                line_text += line_chars[i + 1]["text"]
        page_text.append(line_text)

    return "\n".join(page_text)


def extract_page_metadata(text_content: str, page_number: int) -> Dict[str, Any]:
    """Extracts various metadata features from the text content of a page."""
    metadata = {
        "page_number": page_number,
        "word_count": len(text_content.split()),
        "char_count": len(text_content),
        "has_numbers": bool(re.search(r"\d", text_content)),
        "has_dates": bool(re.search(RE_DATE, text_content)),
        "has_emails": bool(
            re.search(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text_content
            )
        ),
        "has_phone_numbers": bool(re.search(RE_PHONE, text_content)),
        "has_currency_symbols": bool(re.search(RE_CURRENCY, text_content)),
        "language_features": {
            "has_questions": bool(re.search(r"\?", text_content)),
            "has_bullet_lists": bool(
                re.search(r"^\s*[-•*]\s+", text_content, re.MULTILINE)
            ),
            "has_numbered_lists": bool(
                re.search(r"^\s*\d+\.\s+", text_content, re.MULTILINE)
            ),
            "has_potential_headers": bool(
                re.search(RE_HEADER_CANDIDATE, text_content, re.MULTILINE)
            ),
            "sentence_count": len(
                re.findall(r"[.!?]+[\s\"]", text_content)
            )  # Count sentences ending with space or quote
            + (
                1
                if text_content
                and text_content.strip()[-1] in ".!?"
                and not text_content.strip().endswith("...")
                else 0
            ),  # Add one if ends with punctuation
        },
    }

    entities = {
        "dates": re.findall(RE_DATE, text_content),
        "numbers": re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b", text_content),
        "percentages": re.findall(r"\b\d+(?:\.\d+)?%", text_content),
        "capitalized_phrases": re.findall(
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text_content
        ),
    }

    metadata["extracted_entities"] = {
        k: list(set(v)) for k, v in entities.items()
    }  # Deduplicate

    # Calculate entity density (number of entities per 100 words)
    total_entities = sum(len(v) for v in metadata["extracted_entities"].values())
    metadata["entity_density_per_100_words"] = (total_entities * 100) / max(
        metadata["word_count"], 1
    )

    return metadata


def process_page_content(
    page: Page,
    extract_text_flag: bool = True,
    extract_tables_flag: bool = True,
    use_custom_text_extractor: bool = False,
) -> str:
    """
    Processes a single PDF page to extract text and/or tables.
    Allows choosing between pdfplumber's default text extraction and the custom one.
    """
    content_parts = []

    if extract_text_flag:
        if use_custom_text_extractor:
            # print(f"Page {page.page_number}: Using CUSTOM text extractor.") # For debugging
            extracted_text = extract_text_from_page_custom(page)
        else:
            # print(f"Page {page.page_number}: Using PDFPlumber default text extractor.") # For debugging
            extracted_text = (
                page.extract_text(
                    x_tolerance=2, y_tolerance=2, layout=False, keep_blank_chars=False
                )
                or ""
            )

        if extracted_text.strip():
            content_parts.append(extracted_text)

    if extract_tables_flag:
        # More robust table settings could be added here if needed
        # e.g., page.find_tables(table_settings={...})
        tables_on_page = page.extract_tables()
        for i, table_data in enumerate(tables_on_page):
            if table_data:  # Ensure table_data is not empty
                table_markdown = f"\n[TABLE START - {i + 1}]\n"
                table_markdown += convert_table_to_markdown(table_data)
                table_markdown += f"\n[TABLE END - {i + 1}]\n"
                content_parts.append(table_markdown)

    return "\n\n".join(content_parts).strip()


def clean_and_normalize_text_content(text: str) -> str:
    """Cleans and normalizes text for better processing and embedding quality."""
    if not text:
        return ""

    # Basic whitespace normalization
    text = re.sub(r"\s+", " ", text)  # Consolidate multiple whitespace characters
    text = text.strip()

    # Handle hyphenated words at line breaks (simple version)
    text = re.sub(
        r"(\w)-\s*\n\s*(\w)", r"\1\2", text
    )  # Rejoin words split by hyphen and newline

    # Add space between camelCase, number-letter, letter-number for better tokenization
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"(\d)([A-Za-z])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z])(\d)", r"\1 \2", text)

    # Remove common boilerplate like page numbers
    text = re.sub(RE_PAGE_NUMBER_GENERIC, "", text, flags=re.IGNORECASE)

    # Remove lines that consist only of digits (often stray page numbers or list counters)
    text = re.sub(RE_LINE_ONLY_DIGITS, "", text, flags=re.MULTILINE)

    # Remove or replace specific invalid/undesired characters
    # This regex keeps alphanumeric, common punctuation, and some symbols. Adjust as needed.
    text = re.sub(
        RE_INVALID_CHARS_CLEANUP, " ", text
    )  # Replace with space to avoid merging words

    # Re-consolidate whitespace after replacements
    text = re.sub(r"\s+", " ", text).strip()

    # Optional: Convert to lowercase (can be beneficial for some embeddings/models)
    # text = text.lower()

    return text


def calculate_text_content_quality(content: str) -> float:
    """
    Calculates a quality score for a given text content based on various heuristics.
    Score ranges from 0.0 to 1.0.
    """
    if not content or len(content) < QUALITY_MIN_CONTENT_LENGTH:
        return 0.0

    words = content.split()
    num_words = len(words)
    if num_words == 0:
        return 0.0

    # Using re.split on common sentence delimiters. This is a heuristic.
    sentences = [s for s in re.split(r"[.!?]+[\s\"]|\n{2,}", content) if s.strip()]
    num_sentences = len(sentences)
    if (
        num_sentences == 0 and num_words > 5
    ):  # If no clear sentences but words exist, treat as one sentence
        num_sentences = 1
        sentences = [content]
    elif num_sentences == 0:
        return 0.0

    avg_word_len = sum(len(w) for w in words) / num_words
    avg_sent_len = (
        sum(len(s.split()) for s in sentences) / num_sentences if sentences else 0
    )

    # Calculate ratio of "unwanted" characters (those that `clean_and_normalize_text` aims to remove)
    # This is calculated on the *already cleaned* text. A high ratio here might mean
    # the cleaning wasn't fully effective or the content is still noisy.
    # Note: RE_INVALID_CHARS_CLEANUP defines characters to be REMOVED.
    # So, after cleaning, ideally, there should be few of these.
    # A better metric might be character variety or specific noise patterns.
    # For now, let's assume this checks for residual noise.
    num_problematic_chars = len(re.findall(QUALITY_SPECIAL_CHAR_REGEX_CONTENT, content))
    cleanliness_score = max(
        0, 1 - (num_problematic_chars / max(len(content), 1) * 5)
    )  # Penalize if many such chars remain

    structure_score = 0.0
    # Starts with a capital letter (indicative of a sentence start)
    if re.search(r"^\s*[A-Z]", content):
        structure_score += 0.3
    # Ends with a common punctuation mark
    if re.search(r"[.!?]\s*$", content.strip()):
        structure_score += 0.4
    # Contains paragraph breaks (more than one line)
    if (
        "\n" in content or num_sentences > 1
    ):  # Check for explicit newlines or multiple sentences
        structure_score += 0.3
    structure_score = min(structure_score, 1.0)

    # Weighted score calculation
    quality = (
        min(avg_word_len / QUALITY_AVG_WORD_LEN_TARGET, 1.0) * QUALITY_WEIGHT_WORD_LEN
        + min(avg_sent_len / QUALITY_AVG_SENT_LEN_TARGET, 1.0) * QUALITY_WEIGHT_SENT_LEN
        + cleanliness_score * QUALITY_WEIGHT_CLEANLINESS
        + structure_score * QUALITY_WEIGHT_STRUCTURE
    )

    return min(max(quality, 0.0), 1.0)  # Ensure score is between 0 and 1


def process_pdf_document(
    pdf_file_source: Union[
        str, BytesIO, Any
    ],  # Can be path, BytesIO, or file-like object
    extract_text: bool = True,
    extract_tables: bool = True,
    use_custom_text_extraction_method: bool = False,  # Flag to choose text extractor
    page_ids_to_process: Optional[List[int]] = None,
) -> Dict[int, Dict[str, Any]]:
    """
    Processes a PDF document, extracts content page by page, and gathers metadata.
    """
    page_data_map = {}
    document_summary_stats = {
        "total_pages_in_pdf": 0,
        "pages_processed": 0,
        "total_extracted_words": 0,
        "document_contains_tables": False,
        "errors": [],
    }

    try:
        pdf_input_stream = None
        if isinstance(pdf_file_source, BytesIO):
            pdf_input_stream = pdf_file_source
        elif isinstance(pdf_file_source, str):  # Path to file
            pdf_input_stream = open(pdf_file_source, "rb")
        elif hasattr(pdf_file_source, "read"):  # File-like object
            # Ensure it's in binary mode or wrap if necessary
            if isinstance(pdf_file_source.read(0), str):  # Text mode
                raise ValueError("PDF file must be opened in binary mode ('rb').")
            pdf_input_stream = pdf_file_source
        else:
            raise ValueError(
                "Unsupported pdf_file_source type. Provide path, BytesIO, or binary file-like object."
            )

        # Reset stream position if it's a BytesIO or file object that might have been read before
        if hasattr(pdf_input_stream, "seek"):
            pdf_input_stream.seek(0)

        with pdfplumber.open(pdf_input_stream) as pdf:
            document_summary_stats["total_pages_in_pdf"] = len(pdf.pages)

            pages_to_iterate = []
            if page_ids_to_process:
                for pid in page_ids_to_process:
                    if 1 <= pid <= len(pdf.pages):
                        pages_to_iterate.append(
                            pdf.pages[pid - 1]
                        )  # pdf.pages is 0-indexed
                    else:
                        print(f"Warning: Page ID {pid} is out of range. Skipping.")
            else:
                pages_to_iterate = pdf.pages

            for page_obj in tqdm(pages_to_iterate, desc="Processing PDF pages"):
                page_num = page_obj.page_number  # 1-indexed

                try:
                    raw_page_content = process_page_content(
                        page_obj,
                        extract_text_flag=extract_text,
                        extract_tables_flag=extract_tables,
                        use_custom_text_extractor=use_custom_text_extraction_method,
                    )

                    if raw_page_content and raw_page_content.strip():
                        cleaned_page_content = clean_and_normalize_text_content(
                            raw_page_content
                        )

                        if (
                            len(cleaned_page_content.split()) < 10
                        ):  # Skip if too short after cleaning
                            continue

                        page_meta = extract_page_metadata(
                            cleaned_page_content, page_num
                        )

                        # Update document-level table detection
                        if not document_summary_stats[
                            "document_contains_tables"
                        ] and any(
                            "[TABLE START" in part
                            for part in raw_page_content.split("\n\n")
                            if part.strip()
                        ):
                            document_summary_stats["document_contains_tables"] = True

                        document_summary_stats["pages_processed"] += 1
                        document_summary_stats["total_extracted_words"] += page_meta[
                            "word_count"
                        ]

                        # Prepending page number to content is a choice, can be kept or removed
                        # content_with_page_marker = f"[PAGE {page_num}]\n{cleaned_page_content}"

                        page_data_map[page_num] = {
                            "text_content": cleaned_page_content,  # Storing cleaned content
                            "metadata": page_meta,
                            "quality_metrics": {
                                "content_quality_score": calculate_text_content_quality(
                                    cleaned_page_content
                                ),
                                "information_density_score": page_meta[
                                    "entity_density_per_100_words"
                                ],  # Example
                            },
                        }
                except Exception as e_page:
                    error_msg = f"Error processing page {page_num}: {e_page}"
                    print(error_msg)
                    document_summary_stats["errors"].append(error_msg)
                    continue  # Skip to next page

        print("\n--- Document Processing Summary ---")
        print(f"- Total pages in PDF: {document_summary_stats['total_pages_in_pdf']}")
        print(
            f"- Pages successfully processed: {document_summary_stats['pages_processed']}"
        )
        print(
            f"- Total words extracted (from processed pages): {document_summary_stats['total_extracted_words']}"
        )
        print(
            f"- Document contains tables: {'Yes' if document_summary_stats['document_contains_tables'] else 'No'}"
        )
        if document_summary_stats["errors"]:
            print(f"- Errors encountered: {len(document_summary_stats['errors'])}")
            # for err in document_summary_stats["errors"]: print(f"  - {err}")

    except Exception as e_doc:
        print(f"FATAL Error processing PDF document: {e_doc}")
        document_summary_stats["errors"].append(f"Fatal document error: {e_doc}")
    finally:
        # Close the stream if we opened it (i.e., it was a path string)
        if (
            isinstance(pdf_file_source, str)
            and pdf_input_stream
            and not pdf_input_stream.closed
        ):
            pdf_input_stream.close()

    return page_data_map  # , document_summary_stats # Optionally return stats too


class SemanticBoundariesTextSplitter(RecursiveCharacterTextSplitter):
    """
    An advanced text splitter that aims to preserve semantic boundaries more effectively
    by using a curated list of regular expression separators and cleaning up chunk boundaries.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, **kwargs: Any):
        # Prioritized list of separators. Since is_separator_regex=True,
        # all these strings are treated as regular expressions.
        # Ensure regex special characters are properly escaped if they are meant to be literal.
        separators = [
            # Custom table markers (square brackets escaped)
            r"\n\[TABLE START",  # Escape '['
            r"\n\[TABLE END",  # Escape '['
            # Structural elements
            r"\n\n\n+",  # Three or more newlines (already a valid regex pattern)
            r"\n\n",  # Paragraph breaks (two newlines)
            # Markdown style headers (literal '#')
            r"\n# ",
            r"\n## ",
            r"\n### ",
            r"\n#### ",
            # List markers (literal symbols, asterisk escaped)
            r"\n- ",
            r"\n\* ",  # Escape '*' for literal asterisk
            r"\n• ",
            r"\n\d+\.\s+",  # Numbered lists (e.g., "1. Item") - already a valid regex
            # Sentence terminators (literal punctuation, relevant symbols escaped)
            r"\.\n",
            r"\?\n",
            r"!\n",  # Escape '.' and '?'
            r"\. ",
            r"\? ",
            r"! ",  # Escape '.' and '?'
            r"; ",
            r": ",
            # General fallbacks
            r"\n",  # Newlines
            r" ",  # Spaces
            r"",  # Character level (last resort) - empty string is a valid separator
        ]
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,
            is_separator_regex=True,  # Crucial: all separators are treated as regex
            **kwargs,
        )

    def split_text(self, text: str) -> List[str]:
        """Splits text, applying pre-cleaning and post-processing to chunks."""
        # Text is expected to be relatively clean here.
        # The main cleaning (clean_and_normalize_text_content) should happen before
        # passing the text to this splitter if needed.

        raw_chunks = super().split_text(text)

        processed_chunks = []
        for chunk in raw_chunks:
            cleaned_chunk = chunk.strip()

            min_len = (
                self._chunk_size // 10
            )  # Heuristic: min chunk length relative to target size
            if hasattr(self, "min_chunk_length"):  # If defined as an attribute
                min_len = self.min_chunk_length
            elif "TEXT_SPLITTER_MIN_CHUNK_LENGTH" in globals():
                min_len = TEXT_SPLITTER_MIN_CHUNK_LENGTH

            if (
                not cleaned_chunk or len(cleaned_chunk) < min_len
            ):  # Use dynamic or configured min length
                continue

            final_chunk = self._refine_chunk_end(cleaned_chunk, min_len)

            if final_chunk.strip():
                processed_chunks.append(final_chunk)

        return processed_chunks

    def _refine_chunk_end(self, chunk: str, min_acceptable_length: int) -> str:
        """
        Refines the end of a chunk to avoid cutting off sentences abruptly.
        Tries to end on a sentence terminator if the chunk doesn't already.
        """
        chunk = chunk.strip()
        if not chunk:
            return ""

        if chunk.endswith((".", "?", "!", '."', '?"', '!"')):
            return chunk

        last_punct_pos = -1
        # Try to find sentence endings (. ! ?) that are likely actual ends of sentences
        for m in re.finditer(r"[.!?](?=(\s|$)|(\"\s*($|\n))|(\'\s*($|\n)))", chunk):
            last_punct_pos = m.end()

        # If a punctuation is found in the latter part of the chunk (e.g., last 30%)
        # and truncating there doesn't make the chunk too short
        if last_punct_pos != -1 and last_punct_pos > len(chunk) * 0.7:
            potential_chunk = chunk[:last_punct_pos].strip()
            if (
                len(potential_chunk) >= min_acceptable_length * 0.5
            ):  # Ensure not too small
                return potential_chunk

        return chunk


# --- Example Usage (Illustrative) ---
if __name__ == "__main__":
    # This example requires a PDF file named "sample.pdf" in the same directory
    # or replace with a valid path to your PDF.
    # You might also need to `pip install pdfplumber langchain-text-splitters tqdm`

    # Create a dummy PDF for testing if you don't have one
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch

        def create_dummy_pdf(filename="dummy_sample.pdf"):
            c = canvas.Canvas(filename, pagesize=letter)
            width, height = letter

            # Page 1
            c.drawString(
                1 * inch, height - 1 * inch, "Page 1: Introduction and Overview"
            )
            text_obj = c.beginText(1 * inch, height - 1.5 * inch)
            text_obj.textLine(
                "This is the first paragraph of the document. It contains some general information."
            )
            text_obj.textLine(
                "The quick brown fox jumps over the lazy dog. This sentence is for testing. What is this? This is a test."
            )
            text_obj.textLine(
                "This document will explore various topics of interest to data scientists and AI engineers."
            )
            text_obj.textLine(
                "Contact us at dummy.email@example.com or call (555) 123-4567."
            )
            c.drawText(text_obj)
            c.drawString(1 * inch, 5 * inch, "A Simple Table:")
            data = [
                ["Header 1", "Header 2", "Header 3"],
                ["Row 1, Col 1", "Row 1, Col 2", "Value: $100.00"],
                ["Row 2, Col 1", "Row 2, Col 2", "Percentage: 25%"],
            ]

            x_start, y_start = 1 * inch, 4.5 * inch
            row_height = 0.3 * inch
            col_width = 2 * inch
            for i, row in enumerate(data):
                for j, cell in enumerate(row):
                    c.drawString(
                        x_start + j * col_width,
                        y_start - i * row_height,
                        cell if cell else "",
                    )
            c.showPage()

            # Page 2
            c.drawString(1 * inch, height - 1 * inch, "Page 2: Detailed Sections")
            text_obj_p2 = c.beginText(1 * inch, height - 1.5 * inch)
            text_obj_p2.textLine(
                "Section A discusses advanced methodologies. It includes bullet points:"
            )
            text_obj_p2.textLine("- Point one about methodology X.")
            text_obj_p2.textLine(
                "- Point two related to framework Y (released on 10/03/2023)."
            )
            text_obj_p2.textLine(
                "Section B focuses on practical applications. The quality of text can vary."
            )
            text_obj_p2.textLine(
                "Another sentence for splitting. Here is another one. This could be a long sentence that might be split by the text splitter depending on the chunk size and overlap settings. We want to see how it handles this. The goal is to maintain semantic coherence within each chunk as much as possible. This line is quite long to test the splitting behavior effectively."
            )
            c.drawText(text_obj_p2)
            c.save()
            print(f"Created dummy PDF: {filename}")
            return filename

        pdf_file_path = create_dummy_pdf()

        # 1. Process the PDF document
        print(
            f"\nProcessing PDF: {pdf_file_path} using PDFPlumber default text extraction..."
        )
        # Set use_custom_text_extraction_method=True to test the custom extractor
        all_page_data = process_pdf_document(
            pdf_file_path, use_custom_text_extraction_method=False
        )

        if not all_page_data:
            print("No data extracted from PDF.")
        else:
            print(f"\n--- Extracted Data ({len(all_page_data)} pages) ---")
            full_document_text = []
            for page_num, data in sorted(all_page_data.items()):
                print(
                    f"\n[Page {page_num}] (Quality: {data['quality_metrics']['content_quality_score']:.2f}, Info Density: {data['quality_metrics']['information_density_score']:.2f})"
                )
                print(f"  Word Count: {data['metadata']['word_count']}")
                # print(f"  Metadata: {data['metadata']}") # Can be verbose
                # print(f"  Content Preview: {data['text_content'][:200]}...") # Preview content
                full_document_text.append(data["text_content"])

            # Concatenate text from all pages for splitting (or split page by page)
            concatenated_text = "\n\n".join(full_document_text)

            # 2. Initialize the text splitter
            splitter = SemanticBoundariesTextSplitter(chunk_size=300, chunk_overlap=50)

            # 3. Split the concatenated text
            print("\n--- Splitting Text ---")
            chunks = splitter.split_text(concatenated_text)

            print(f"Number of chunks created: {len(chunks)}")
            for i, chunk in enumerate(chunks):
                chunk_quality = calculate_text_content_quality(
                    chunk
                )  # Recalculate for chunk
                print(
                    f"\n--- Chunk {i + 1} (Length: {len(chunk)}, Quality: {chunk_quality:.2f}) ---"
                )
                print(chunk)
                print("--------------------")

    except ImportError:
        print("reportlab is not installed. Skipping dummy PDF creation.")
        print("Please provide a 'sample.pdf' or install reportlab to run the example.")
    except Exception as e:
        print(f"An error occurred during the example usage: {e}")
