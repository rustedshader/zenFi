import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from langchain_google_community import BigQueryVectorSearch
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_vertexai import VertexAIEmbeddings
import json
from google.cloud import bigquery
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_community.vectorstores import (
    bigquery_vector_search as bigquery_vector_search_module,
)
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()


class BigQueryVectorSearchLocal(BigQueryVectorSearch):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _search_with_score_and_embeddings_by_vector(
        self,
        embedding: List[float],
        k: int = bigquery_vector_search_module.DEFAULT_TOP_K,
        filter: Optional[Dict[str, Any]] = None,
        brute_force: bool = False,
        fraction_lists_to_search: Optional[float] = None,
    ) -> List[Tuple[Document, List[float], float]]:
        from google.cloud import bigquery

        if not self._have_index and not self._creating_index:
            self._initialize_vector_index()
        filter_expr = "TRUE"
        if filter:
            filter_expressions = []
            for i in filter.items():
                if isinstance(i[1], float):
                    expr = (
                        "ABS(CAST(JSON_VALUE("
                        f"base.`{self.metadata_field}`,'$.{i[0]}') "
                        f"AS FLOAT64) - {i[1]}) "
                        f"<= {sys.float_info.epsilon}"
                    )
                else:
                    val = str(i[1]).replace('"', '\\"')
                    expr = (
                        f"JSON_VALUE(base.`{self.metadata_field}`,'$.{i[0]}')"
                        f' = "{val}"'
                    )
                filter_expressions.append(expr)
            filter_expression_str = " AND ".join(filter_expressions)
            filter_expr += f" AND ({filter_expression_str})"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("v", "FLOAT64", embedding),
            ],
            use_query_cache=False,
            priority=bigquery.QueryPriority.BATCH,
        )
        if self.distance_strategy == DistanceStrategy.EUCLIDEAN_DISTANCE:
            distance_type = "EUCLIDEAN"
        elif self.distance_strategy == DistanceStrategy.COSINE:
            distance_type = "COSINE"
        else:
            distance_type = "EUCLIDEAN"
        if brute_force:
            options_string = ",options => '{\"use_brute_force\":true}'"
        elif fraction_lists_to_search:
            if fraction_lists_to_search == 0 or fraction_lists_to_search >= 1.0:
                raise ValueError(
                    "`fraction_lists_to_search` must be between 0.0 and 1.0"
                )
            options_string = (
                ',options => \'{"fraction_lists_to_search":'
                f"{fraction_lists_to_search}}}'"
            )
        else:
            options_string = ""
        query = f"""
            SELECT
                base.*,
                distance AS _vector_search_distance
            FROM VECTOR_SEARCH(
                TABLE `{self.full_table_id}`,
                "{self.text_embedding_field}",
                (SELECT @v AS {self.text_embedding_field}),
                distance_type => "{distance_type}",
                top_k => {k}
                {options_string}
            )
            WHERE {filter_expr}
            LIMIT {k}
        """
        document_tuples: List[Tuple[Document, List[float], float]] = []
        job = self.bq_client.query(
            query, job_config=job_config, api_method=bigquery.enums.QueryApiMethod.QUERY
        )
        for row in job:
            metadata = row[self.metadata_field]
            if metadata:
                try:
                    metadata = json.loads(metadata)
                except TypeError:
                    pass
            else:
                metadata = {}
            metadata["__id"] = row[self.doc_id_field]
            metadata["__job_id"] = job.job_id
            doc = Document(page_content=row[self.content_field], metadata=metadata)
            document_tuples.append(
                (doc, row[self.text_embedding_field], row["_vector_search_distance"])
            )
        return document_tuples


class Properties:
    def __init__(self, project_id, region, dataset, table):
        self.project_id = project_id
        self.region = region
        self.dataset = dataset
        self.table = table


GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
project_id = os.environ.get("PROJECT_ID")


class EnhancedVectorStoreFactory:
    def __init__(self, properties):
        self.embedding = VertexAIEmbeddings(
            model_name="text-embedding-005", project=project_id
        )
        self.properties = properties

    def create_store(self):
        store = BigQueryVectorSearchLocal(
            project_id=self.properties.project_id,
            dataset_name=self.properties.dataset,
            table_name=self.properties.table,
            location=self.properties.region,
            embedding=self.embedding,
            distance_strategy=DistanceStrategy.COSINE,
        )
        return store


def create_vectors_enhanced(
    project_id, region, dataset, table, metadata, texts: List[str], truncate=False
):
    """Enhanced vector creation with better storage strategy"""
    properties = Properties(project_id, region, dataset, table)
    store = EnhancedVectorStoreFactory(properties).create_store()

    client = bigquery.Client(project=properties.project_id, location=properties.region)
    client.create_dataset(dataset=dataset, exists_ok=True)

    if truncate:
        query_job = client.query(f"""
        TRUNCATE TABLE `{properties.project_id}.{properties.dataset}.{properties.table}`
        """)
        query_job.result()

    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_metadata = metadata[i : i + batch_size]

        try:
            store.add_texts(metadatas=batch_metadata, texts=batch_texts)
            print(
                f"Processed batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}"
            )
        except Exception as e:
            print(f"Error processing batch {i // batch_size + 1}: {e}")
            continue
