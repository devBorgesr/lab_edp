# Diagnostico de Retrieval — imagem minima.
#
# Construida DEPOIS de a instalacao local funcionar, nao antes: um Dockerfile
# que esconde uma dependencia nao declarada so adia a descoberta.
FROM python:3.11-slim

WORKDIR /app

# Dependencias primeiro, para a camada aproveitar cache entre builds.
COPY pyproject.toml README.md ./
COPY auditor ./auditor
RUN pip install --no-cache-dir ".[http]"

# Usuario sem privilegio: o servico recebe material de terceiros.
RUN useradd --create-home --uid 10001 auditor \
 && mkdir -p /dados && chown -R auditor:auditor /dados /app
USER auditor

VOLUME ["/dados"]
EXPOSE 8080

# `ready` confere workspace gravavel e registro; nao executa auditoria.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/ready', timeout=4).status==200 else 1)"

ENTRYPOINT ["python", "-m", "auditor.api"]
CMD ["--base", "/dados", "--host", "0.0.0.0", "--port", "8080"]
