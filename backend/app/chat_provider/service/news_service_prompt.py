finance_news_topic_system_instructions = """
<Top Finance News Results>
1. Review the search results for the top financial news carefully.
2. Get the most important news topics.
</Top Finance News Results>
<Todays Date>
It is todays date.
</Todays Date>

"""

get_finance_news_topics_prompt = """
<Todays Date>
{date}
</Todays Date>
<Top Finance News Results>
{search_results}
</Top Finance News Results>

Based on topic Finance News Data Gathered from web generate top search queries based on the top news headlines in the Top Finance News Result.
"""

query_writer_instructions = """You are an expert technical writer crafting targeted web search queries that will gather comprehensive information for writing a technical report section.

<Report topic>
{topic}
</Report topic>

<Task>
Your goal is to generate search queries that will help gather comprehensive information above the section topic. 

The queries should:

1. Be related to the topic 
2. Examine different aspects of the topic

Make the queries specific enough to find high-quality, relevant sources.
</Task>

<Format>
Call the Queries tool 
</Format>
"""


topic_specific_query_instructions = """You are an expert techincal writer crafting target web search queries that will be the main topic and headlines of the todays financial news based on todays top news financial data.
<Top Finance News Results>
{search_response}
</Top Finance News Results>
Based on topic Finance News Data Gathered from web generate top search queries based on the top news headlines in the Top Finance News Result.

Make the queries specific enough to find high-quality, relevant sources.

<Format>
Call the Queries tool 
</Format>
"""

generate_news_instructions = """
<News Search Response>
{news_search_response}
</News Search Response>
<Todays Date>
{date}
</Todays Date>
<Task>
You are an expert financial news writer tasked with generating a structured financial news report based on the provided news search response. The report should summarize the TOP MULTIPLE financial news topics, provide detailed content, and list relevant sources.

The report should:
1. Identify the MULTIPLE most important financial news topics from the news search response (aim for 3-5 different topics).
2. Provide a concise summary of the key points for each topic.
3. Include detailed content explaining the significance of each topic.
4. Cite high-quality, relevant sources from the news search response.
5. Ensure each news item is structured according to the FinanceNews model, with fields for topic, description, content, sources, and summary.

Make the report clear, professional, and suitable for a technical audience interested in financial markets.
Generate MULTIPLE distinct news items covering different financial topics from the search results.
</Task>
<Format>
Return the output as a FinanceNewsReport object containing multiple FinanceNews items in the news_items field.
</Format>
"""
