#!/usr/bin/env python
# coding: utf-8

# In[31]:


import requests
import json
import os


# In[5]:


db_endpoint = 'https://db.ygoprodeck.com/api/v7/cardinfo.php'


# In[6]:


response = requests.get(db_endpoint)


# In[29]:


db = response.json()['data']


# In[32]:


if os.path.exists('ygodb.json'):
    os.remove('ygodb.json')
    
with open('ygodb.json','w') as f:
    json.dump(db,f, indent = 4)


# In[25]:


import psycopg2


# In[26]:


import pandas


# In[33]:


df = pandas.read_json('ygodb.json')


# In[42]:


df.columns


# In[47]:


df = df[['id','name','ygoprodeck_url']]


# In[45]:


from sentence_transformers import SentenceTransformer


# In[46]:


model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')


# In[193]:


ids = df['id'].values
names = df['name'].values
urls = df['ygoprodeck_url'].values


# In[194]:


embeddings = model.encode(names)


# In[58]:


embeddings


# In[229]:


tuples = zip(ids,names,embeddings)


# In[232]:


tuples = list(tuples)


# In[63]:


import psycopg2


# In[238]:


connection_string = 'postgres://postgres:skystrikeraceraye@db.fhfpshtdphuarmkjazba.supabase.co:5432/postgres'


# In[262]:


connection = psycopg2.connect(connection_string)


# In[263]:


cur = connection.cursor()


# In[256]:


# cur.execute("""
# CREATE TABLE cards(
# id int8 PRIMARY KEY,
# name TEXT,
# ygoprodeck_url TEXT,
# name_vector VECTOR(384)
# )
#             """)


# In[264]:


query = "UPDATE cards SET name_vector = %s WHERE id = %s"
for uid,name,vec in tuples:
    uid = int(uid)
    vec_list = vec.tolist()
    cur.execute(query, (vec_list,uid))


# In[265]:


connection.commit()
cur.close()
connection.close()


# In[279]:


def vectorsearch(query: str) -> None:
    user_search_vec = model.encode(query)
    search_query = f"SELECT * FROM cards ORDER BY name_vector <-> '{user_search_vec.tolist()}' LIMIT 5;"
    with psycopg2.connect(connection_string) as conn:
        cur = conn.cursor()
        cur.execute(search_query)
        responses = cur.fetchall()
    for response in responses:
        print(response[1])


# In[291]:


vectorsearch("rika strena")


# In[ ]:




