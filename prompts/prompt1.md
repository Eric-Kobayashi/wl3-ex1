I want to setup this repo for building a natual lagnuage processing app using Pydantic AI. It should
- take a YouTube Channel (get it from .env) which is a talk show (leading host + guests including domain experts and politicians, doing interview), and list all of its videos
- find out if there is transcript of that video already provided 
- if it is, download that transcropt and add to a local database
- it there isn't, add it to a database as well but mark it as untranscripted
- the above will be extraction
- second step is to classfy the transcripts of each video into different categories using a language model (hosted by Ollama locally), and then label them and put them in the database
- the goal is to extract a certain topic, and analyse the rheotics, and using natural language processing to turn them into a manifold and analyse its shift over time. This is an extra step that is post hoc analysis based on the database

Instructions for building the app:
- use uv for dependencies
- use youtube-dl library
- use Makefile for operatiosn such as extract, analyse, build...
- use sqlite3 for database

the app should be command line facing for now.