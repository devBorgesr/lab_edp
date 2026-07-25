"""
sujeitos — sistemas-sob-inspecao que a bancada sabe operar.

Cada subpacote aqui implementa o Protocol Sujeito (bancada/sujeito.py) para um
sistema especifico (RAG ou analogo). Todo conhecimento de interno do sistema
(schema de store, atributos privados, layout em disco) mora aqui — nunca em
bancada/.
"""
