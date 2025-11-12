import re
import base64
import html
import requests


def consultar_teor(numero_processo: str, expediente: str, cpf: str, senha: str, debug=False):
    """
    Consulta o teor de uma comunicação processual no PJe/TJPI,
    usando as credenciais do usuário (CPF/senha informados no app).
    Retorna (sucesso, texto_html).
    """
    url = "https://pje.tjpi.jus.br/1g/intercomunicacao?wsdl"
    headers = {"Content-Type": "text/xml; charset=utf-8"}

    body = f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                      xmlns:ser="http://www.cnj.jus.br/servico-intercomunicacao-2.2.2/"
                      xmlns:tip="http://www.cnj.jus.br/tipos-servico-intercomunicacao-2.2.2">
       <soapenv:Header/>
       <soapenv:Body>
          <ser:consultarTeorComunicacao>
             <tip:idConsultante>{cpf}</tip:idConsultante>
             <tip:senhaConsultante>{senha}</tip:senhaConsultante>
             <tip:numeroProcesso>{numero_processo}</tip:numeroProcesso>
             <tip:identificadorAviso>{expediente}</tip:identificadorAviso>
          </ser:consultarTeorComunicacao>
       </soapenv:Body>
    </soapenv:Envelope>
    """

    try:
        response = requests.post(url, data=body.encode("utf-8"), headers=headers, timeout=90)
        raw_response = response.content.decode("utf-8", errors="ignore")

        # Detecta se é multipart
        if not re.search(r'--uuid:[a-f0-9\-]{36}', raw_response):
            if debug:
                print(f"ℹ️ Resposta não-multipart para {numero_processo}")
            return False, raw_response

        # Extrai o conteúdo HTML direto ou base64
        match = re.search(r'<xop:Include[^>]*href="cid:([^"]+)"', raw_response)
        if not match:
            return False, None

        cid = match.group(1)
        pattern_cid = f"Content-ID:\\s*<{re.escape(cid)}>"
        cid_match = re.search(pattern_cid, raw_response, re.IGNORECASE)
        if not cid_match:
            return False, None

        start = cid_match.end()
        next_boundary = raw_response.find("--uuid", start)
        attachment = raw_response[start:next_boundary]

        # Extrai apenas a parte útil
        parts = attachment.split("\r\n\r\n", 1)
        content = parts[1].strip() if len(parts) == 2 else attachment.strip()

        # HTML direto ou base64
        if content.startswith("<"):
            texto_documento = content
        else:
            decoded = base64.b64decode(re.sub(r"[\r\n\s]", "", content))
            try:
                texto_documento = decoded.decode("utf-8")
            except UnicodeDecodeError:
                texto_documento = decoded.decode("latin-1", errors="ignore")

        # Remove entidades HTML
        texto_documento = html.unescape(texto_documento)
        return True, texto_documento

    except Exception as e:
        if debug:
            print(f"❌ Erro ao consultar teor ({numero_processo}): {e}")
        return False, None