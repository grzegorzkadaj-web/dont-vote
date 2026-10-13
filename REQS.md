# Vision
Web application which helps people to find out more about political parties before they vote.

From technical perspective that is RAG application where parties programmes are stored in Vector DB.4
# Features
- lets users to find out more about political partie's programmes
- shows on diagram where particular parties is placed when it comes to left-wing and right-wing views
# Requirements
## Business
- users should be able to ask a question, for example: what do parties say about health care system? what is party X opinion on abortion?
- the answer or user question should consists of: answer itself, link to sources (based on meta data from vector db), party name and simple voting form if answer satisfies user
## Technical
- application will be hosted on Railway
- frontend should be written in Next.js
- backend should be written in Python using LangChain, TavilyCrawl, TavilyExtract, TavilyMap
- as application should support RAG architecture it will be integrated with Pinecone