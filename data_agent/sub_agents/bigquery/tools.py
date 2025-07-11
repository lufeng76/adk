# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This file contains the tools used by the database agent."""

import datetime
import logging
import os
import re
import requests

# from data_science.utils.utils import get_env_var
from google.adk.tools import ToolContext
from google.cloud import bigquery
from google.genai import Client, types

# from .chase_sql import chase_constants

# Assume that `BQ_PROJECT_ID` is set in the environment. See the
# `data_agent` README for more details.
project = os.getenv("BQ_PROJECT_ID", None)
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
llm_client = Client(vertexai=True, project=project, location=location)

MAX_NUM_ROWS = 80


database_settings = None
bq_client = None

billing_uri = "https://cloud.google.com/billing/docs/how-to/export-data-bigquery-tables/detailed-usage"
billing_sample_uri = "https://cloud.google.com/billing/docs/how-to/bq-examples"

def fetch_web_content(url):
    """
    Fetch content from a web URL.
    
    Args:
        url (str): The URL to fetch content from
        
    Returns:
        str: The HTML content of the webpage
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return None

def get_env_var(var_name):
  """Retrieves the value of an environment variable.

  Args:
    var_name: The name of the environment variable.

  Returns:
    The value of the environment variable, or None if it is not set.

  Raises:
    ValueError: If the environment variable is not set.
  """
  try:
    value = os.environ[var_name]
    return value
  except KeyError:
    raise ValueError(f'Missing environment variable: {var_name}')


def get_bq_client():
    """Get BigQuery client."""
    global bq_client
    if bq_client is None:
        bq_client = bigquery.Client(project=get_env_var("BQ_PROJECT_ID"))
    return bq_client


def get_database_settings():
    """Get database settings."""
    global database_settings
    if database_settings is None:
        database_settings = update_database_settings()
    return database_settings


def update_database_settings():
    """Update database settings."""
    global database_settings
    ddl_schema,table_id = get_bigquery_schema(
        get_env_var("BQ_DATASET_ID"),
        client=get_bq_client(),
        project_id=get_env_var("BQ_PROJECT_ID"),
    )
    database_settings = {
        "prototype_billing_table": table_id,        
        "bq_project_id": get_env_var("BQ_PROJECT_ID"),
        "bq_dataset_id": get_env_var("BQ_DATASET_ID"),
        "bq_ddl_schema": ddl_schema,
        # Include ChaseSQL-specific constants.
        # **chase_constants.chase_sql_constants_dict,
    }
    return database_settings


def get_bigquery_schema(dataset_id, client=None, project_id=None):
    """Retrieves schema and generates DDL with example values for a BigQuery dataset.

    Args:
        dataset_id (str): The ID of the BigQuery dataset (e.g., 'my_dataset').
        client (bigquery.Client): A BigQuery client.
        project_id (str): The ID of your Google Cloud Project.

    Returns:
        str: A string containing the generated DDL statements.
    """

    if client is None:
        client = bigquery.Client(project=project_id)

    # dataset_ref = client.dataset(dataset_id)
    dataset_ref = bigquery.DatasetReference(project_id, dataset_id)

    ddl_statements = ""
    table_id = ""

    for table in client.list_tables(dataset_ref):
        if 'gcp_billing_export_resource_v1_' not in table.table_id:
            continue
        table_id = table.table_id        
        table_ref = dataset_ref.table(table.table_id)
        table_obj = client.get_table(table_ref)

        # Check if table is a view
        if table_obj.table_type != "TABLE":
            continue

        ddl_statement = f"CREATE OR REPLACE TABLE `{table_ref}` (\n"

        for field in table_obj.schema:
            ddl_statement += f"  `{field.name}` {field.field_type}"
            if field.mode == "REPEATED":
                ddl_statement += " ARRAY"
            if field.description:
                ddl_statement += f" COMMENT '{field.description}'"
            ddl_statement += ",\n"

        ddl_statement = ddl_statement[:-2] + "\n);\n\n"

        # Add example values if available (limited to first row)
        rows = client.list_rows(table_ref, max_results=5).to_dataframe()
        if not rows.empty:
            ddl_statement += f"-- Example values for table `{table_ref}`:\n"
            for _, row in rows.iterrows():  # Iterate over DataFrame rows
                ddl_statement += f"INSERT INTO `{table_ref}` VALUES\n"
                example_row_str = "("
                for value in row.values:  # Now row is a pandas Series and has values
                    if isinstance(value, str):
                        example_row_str += f"'{value}',"
                    elif value is None:
                        example_row_str += "NULL,"
                    else:
                        example_row_str += f"{value},"
                example_row_str = (
                    example_row_str[:-1] + ");\n\n"
                )  # remove trailing comma
                ddl_statement += example_row_str

        ddl_statements += ddl_statement

    return ddl_statements, table_id


def initial_bq_nl2sql(
    question: str,
    tool_context: ToolContext,
) -> str:
    """Generates an initial SQL query from a natural language question.

    Args:
        question (str): Natural language question.
        tool_context (ToolContext): The tool context to use for generating the SQL
          query.

    Returns:
        str: An SQL statement to answer this question.
    """

    prompt_template = """
You are a BigQuery SQL expert tasked with answering user's questions about BigQuery tables by generating SQL queries in the GoogleSql dialect.  Your task is to write a Bigquery SQL query that answers the following question while using the provided context.

**Guidelines:**

- **Table Referencing:** Always use the full table name with the database prefix in the SQL statement.  Tables should be referred to using a fully qualified name with enclosed in backticks (`) e.g. `project_name.dataset_name.table_name`.  Table names are case sensitive.
- **Joins:** Join as few tables as possible. When joining tables, ensure all join columns are the same data type. Analyze the database and the table schema provided to understand the relationships between columns and tables.
- **Aggregations:**  Use all non-aggregated columns from the `SELECT` statement in the `GROUP BY` clause.
- **SQL Syntax:** Return syntactically and semantically correct SQL for BigQuery with proper relation mapping (i.e., project_id, owner, table, and column relation). Use SQL `AS` statement to assign a new name temporarily to a table column or even a table wherever needed. Always enclose subqueries and union queries in parentheses.
- **Column Usage:** Use *ONLY* the column names (column_name) mentioned in the Table Schema. Do *NOT* use any other column names. Associate `column_name` mentioned in the Table Schema only to the `table_name` specified under Table Schema.
- **FILTERS:** You should write query effectively  to reduce and minimize the total rows to be returned. For example, you can use filters (like `WHERE`, `HAVING`, etc. (like 'COUNT', 'SUM', etc.) in the SQL query.
- **LIMIT ROWS:**  The maximum number of rows returned should be less than {MAX_NUM_ROWS}.

**Schema:**

The database structure is defined by the following table schemas (possibly with sample rows):

```
{SCHEMA}
```

**Natural language question:**

```
{QUESTION}
```

**Think Step-by-Step:** Carefully consider the schema, question, guidelines, and best practices outlined above to generate the correct BigQuery SQL.

   """

    ddl_schema = tool_context.state["database_settings"]["bq_ddl_schema"]

    prompt = prompt_template.format(
        MAX_NUM_ROWS=MAX_NUM_ROWS, SCHEMA=ddl_schema, QUESTION=question
    )

    # Create content parts
    content_parts = [
        # Add the text prompt as the first part
        types.Part.from_text(text=prompt),
        # Add the biling mannual from a web URI
        types.Part.from_text(text=fetch_web_content(billing_uri)),    
        # Add the biling sample from a web URI
        types.Part.from_text(text=fetch_web_content(billing_sample_uri)),               
        # Add the PDF file from a GCS URI
        # types.Part.from_uri(
        #     file_uri="gs://sunivy-for-example-public/Structure of Detailed data export  _  Cloud Billing  _  Google Cloud.pdf", mime_type="application/pdf")
    ]    

    try:
        response = llm_client.models.generate_content(
            model=os.getenv("BASELINE_NL2SQL_MODEL"),
            contents=content_parts,
            config={"temperature": 0.1},
        )

        sql = response.text
    except Exception as e:
        logging.error(f"Error using Vertex AI model: {e}")
        # Fallback to LiteLLM
        logging.info("Falling back to LiteLLM")
        raise

    logging.info(prompt)
    
    if sql:
        sql = sql.replace("```sql", "").replace("```", "").strip()

    tool_context.state["raw_sql"] = sql
    tool_context.state["question"] = question
    
    return sql


def run_bigquery_validation(
    sql_string: str,
    tool_context: ToolContext,
) -> str:
    """Validates BigQuery SQL syntax and functionality.

    This function validates the provided SQL string by attempting to execute it
    against BigQuery in dry-run mode. It performs the following checks:

    1. **SQL Cleanup:**  Preprocesses the SQL string using a `cleanup_sql`
    function
    2. **DML/DDL Restriction:**  Rejects any SQL queries containing DML or DDL
       statements (e.g., UPDATE, DELETE, INSERT, CREATE, ALTER) to ensure
       read-only operations.
    3. **Syntax and Execution:** Sends the cleaned SQL to BigQuery for validation.
       If the query is syntactically correct and executable, it retrieves the
       results.
    4. **Result Analysis:**  Checks if the query produced any results. If so, it
       formats the first few rows of the result set for inspection.

    Args:
        sql_string (str): The SQL query string to validate.
        tool_context (ToolContext): The tool context to use for validation.

    Returns:
        str: A message indicating the validation outcome. This includes:
             - "Valid SQL. Results: ..." if the query is valid and returns data.
             - "Valid SQL. Query executed successfully (no results)." if the query
                is valid but returns no data.
             - "Invalid SQL: ..." if the query is invalid, along with the error
                message from BigQuery.
    """

    def cleanup_sql(sql_string):
        """Processes the SQL string to get a printable, valid SQL string."""

        # 1. Remove backslashes escaping double quotes
        sql_string = sql_string.replace('\\"', '"')

        # 2. Remove backslashes before newlines (the key fix for this issue)
        sql_string = sql_string.replace("\\\n", "\n")  # Corrected regex

        # 3. Replace escaped single quotes
        sql_string = sql_string.replace("\\'", "'")

        # 4. Replace escaped newlines (those not preceded by a backslash)
        sql_string = sql_string.replace("\\n", "\n")

        # 5. Add limit clause if not present
        if "limit" not in sql_string.lower():
            sql_string = sql_string + " limit " + str(MAX_NUM_ROWS)

        return sql_string

    logging.info("Validating SQL: %s", sql_string)
    sql_string = cleanup_sql(sql_string)
    logging.info("Validating SQL (after cleanup): %s", sql_string)

    final_result = {"query_result": None, "error_message": None}

    # More restrictive check for BigQuery - disallow DML and DDL
    if re.search(
        r"(?i)(update|delete|drop|insert|create|alter|truncate|merge)", sql_string
    ):
        final_result["error_message"] = (
            "Invalid SQL: Contains disallowed DML/DDL operations."
        )
        return final_result

    try:
        query_job = get_bq_client().query(sql_string)
        results = query_job.result()  # Get the query results

        if results.schema:  # Check if query returned data
            rows = [
                {
                    key: (
                        value
                        if not isinstance(value, datetime.date)
                        else value.strftime("%Y-%m-%d")
                    )
                    for (key, value) in row.items()
                }
                for row in results
            ][
                :MAX_NUM_ROWS
            ]  # Convert BigQuery RowIterator to list of dicts
            # return f"Valid SQL. Results: {rows}"
            final_result["query_result"] = rows

            tool_context.state["query_result"] = rows

        else:
            final_result["error_message"] = (
                "Valid SQL. Query executed successfully (no results)."
            )

    except (
        Exception
    ) as e:  # Catch generic exceptions from BigQuery  # pylint: disable=broad-exception-caught
        final_result["error_message"] = f"Invalid SQL: {e}"

    print("\n run_bigquery_validation final_result: \n", final_result)

    return final_result

def expand_to_actual_billing_tables(question: str, raw_sql: str, tool_context: ToolContext):

    prompt_template = """
You will be given an input SQL statement that operates on a single Google Cloud Platform (GCP) billing export table: `{prototype_table}`.
Your task is to adapt this SQL statement to work with a list of different customer-specific GCP billing export tables. These customer tables share the exact same schema and logical structure as the original table.
The four customer billing tables are:
{target_tables}

Requirements for the Output SQL:
1. Combine Data: Use UNION ALL to combine data from the a list of customer billing tables. If there is only one table, use that table directly without UNION ALL.
1.1 In order to generate valid SQL, please list all columns in the union statement, instead of select *, eg. SELECT billing_account_id, service, sku, usage_start_time, usage_end_time, `project`, `labels`, `system_labels`, location, resource, `tags`, export_time, cost, currency, currency_conversion_rate, usage, `credits`, invoice, cost_type, adjustment_info, price, cost_at_list, transaction_type, seller_name, subscription FROM ...
2. Partition Filtering:
2.1 For each individual customer table query within the UNION ALL structure, add a WHERE clause to filter on the _PARTITIONTIME pseudo-column.
2.2 The filter condition should be: TIMESTAMP_TRUNC(_PARTITIONTIME, DAY) BETWEEN relevant_query_start_date_minus_1_month AND relevant_query_end_date_plus_1_month.
2.2.1 relevant_query_start_date_minus_1_month and relevant_query_end_date_plus_1_month should be a YYYY-MM-DD STRING, DO NOT CAST IT INTO DATE TYPE. eg: TIMESTAMP_TRUNC(_PARTITIONTIME, DAY) BETWEEN '2024-01-01' AND '2024-03-31'
2.3 Determining the range:
2.3.1 Identify if the original input SQL has any date range filters, on usage_start_time or invoice.month.
2.3.2 If such filters exist, relevant_query_start_date_minus_1_month should be approximately 1 month before the earliest date in those filters, and relevant_query_end_date_plus_1_month should be approximately 1 month after the latest date.
2.3.3 If the original query does not have explicit date range filters, do not add partition filtering.
3. Apply Original Logic: The overall structure of the original input SQL (its SELECT list, main WHERE conditions (other than the new partition filter), GROUP BY, JOINs, etc.) should be applied to the result of the UNION ALL of the pre-filtered customer tables. This typically means the UNION ALL part will be in a Common Table Expression (CTE) or a subquery.

question:
{question}

input SQL:
{raw_sql}

output SQL:
    
    """
    prototype_billing_table = tool_context.state["database_settings"]["prototype_billing_table"]

    project_list = os.getenv('TARGET_BILLING_TABLES',
                             prototype_billing_table).split(',')
    prompt = prompt_template.format(
        prototype_table=prototype_billing_table,
        target_tables='/n'.join(project_list),
        raw_sql=raw_sql, question=question
    )

    # Create a list of content parts including both the text prompt and PDF
    from google.genai import types

    # Create content parts
    content_parts = [
        types.Part.from_text(text=prompt),
    ]

    try:
        response = llm_client.models.generate_content(
            model=os.getenv("BASELINE_NL2SQL_MODEL",
                            "gemini-2.5-pro-preview-05-06"),
            contents=content_parts,
            config={"temperature": 0.1},
        )
        sql = response.text
    except Exception as e:
        logging.error(f"Error using Vertex AI model: {e}")
        logging.info("Falling back to LiteLLM")
        raise

    tool_context.state["final_sql"] = sql

    return sql