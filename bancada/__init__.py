"""
bancada — nucleo da Bancada de Contexto (Burp Suite aplicado a LLMs), agnostico
de sujeito.

PROIBIDO importar edp.*, sujeitos.* ou qualquer subpacote de um sistema
concreto (runtime, memory, llm, clock, echo_chamber, retrieval_hybrid,
embeddings, memory_classifier) — ver tests/test_fronteira.py. Quem ensina a
bancada a falar de um sistema especifico e o adaptador em sujeitos/<nome>/.

Base: prontuario (store longitudinal) + isolamento (sessao de lab dedicada
sobre um Sujeito) + sujeito (o Protocol). Construido para durar tempo
indeterminado.
"""
