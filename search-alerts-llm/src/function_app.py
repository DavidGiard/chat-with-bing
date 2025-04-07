import azure.functions as func
import logging
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
from config import AZURE_SEARCH_INDEX_NAME, AZURE_SEARCH_API_KEY, AZURE_OPENAI_DEPLOYMENT_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_KEY, AZURE_SEARCH_ENDPOINT

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="alerts")
def alerts(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    query = req.params.get('name')
    if not query:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            query = req_body.get('name')

        client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=AZURE_SEARCH_INDEX_NAME,
            credential=AzureKeyCredential(AZURE_SEARCH_API_KEY)
        )

        # query = question = input("Enter your question: ")
        # query = "What triggers the CDSC Amount Threshold?"
        # query = "What are exceptions to the age max rule?"
        # query = "What triggers an alert?"
        results = client.search(query)
        logging.info(f"Search results for query: '{query}'") 

        iterator = iter(results)
        if not any(iterator):
            logging.info("No results found.")
            return

        # Collect the relevant document snippets
        relevant_documents = []
        for result in results:
            relevant_documents.append(result['content'])

        logging.info("Retrieved Documents:")
        for doc in relevant_documents:
            logging.info(doc)

        oaiClient = AzureOpenAI(
            api_version="2024-10-21",
            azure_endpoint=AZURE_OPENAI_DEPLOYMENT_ENDPOINT,
            api_key=AZURE_OPENAI_DEPLOYMENT_KEY,
        )

        sys_prompt = f'''
        Answer questions about processes and filters found in the work documents. Be professional in your response.
        ++++
        {relevant_documents[0]}
        ++++
        '''
        new_msg = relevant_documents[0] 

        history=[]
        inputs = [
            {'role':'system', 'content':sys_prompt},
            *history, 
            {'role':'user','content':new_msg}
        ]
        openAiResult = oaiClient.chat.completions.create(
            model="gpt-4o",
            messages=inputs,
            temperature=0.5,
            max_tokens=450,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0.6,
            stop=["\n", " Human:", " AI:"],
        )

        openAiMessage = openAiResult.choices[0].message

        logging.info("============================")
        logging.info(f'Query {query}')
        logging.info("Response:")
        logging.info(openAiMessage.content)

        return func.HttpResponse(
            openAiMessage.content,
            status_code=200
        )
