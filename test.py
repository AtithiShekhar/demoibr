import chromadb

client = chromadb.HttpClient(
    host="internal-chroma-lb-xxxx.elb.amazonaws.com",
    port=8000
)

col = client.get_collection("my_collection")
print(col.get())