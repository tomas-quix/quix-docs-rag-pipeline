# Welcome to the Quix "Chat with Docs" prototype 🚀🤖

This internal prototype is designed to help you find the information you need from Quix Docs or other sources with the help of large language models 

This prototype is hosted in Quix Cloud but uses the Qdrant Cloud as a search database. 

If it works well, we'll consider making it public.

## How it Works ⚙️

 * You ask chatbot a question (such as "how do I configure the _auto.offset.reset_ parameter")
 * The chatbot searches the Qdrant database for text fragments that are semantically similar to your question (we imported the Quix Docs into the Qdrant db)
 * The chatbot sends top 3 matching results (including the content) to OpenAI's GPT4 as well as your original question, and instructs GPT4 to use the content to answer your question.
   * If content from the matching documents is not helpful enough to answer the question, GPT4 will say so (and won't try to make up some unhelpful nonsense).
 * Assuming some matching content was found, GPT4 will provide a natural-language answer to your question after "reading" the content.

## Ask a Question 💡

If you've forgotten how to do something in Quix, (such as implementing windowed calculations or replaying a topic), ask the chatbot, and it will answer the question based on the existing content. If it can't answer your question, chances are we need to add it to the docs.

So, if you help test the chatbot, you're indirectly helping us improve the docs!

**NOTE:** _Each search query is logged (along with the matching documents, and the chatbot's answer) to a Kafka topic so that we can troubleshoot what's working and what's not._

