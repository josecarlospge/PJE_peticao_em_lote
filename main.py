import streamlit as st
import pandas as pd
import base64, hashlib, re, html
from datetime import datetime
from time import sleep
import requests
import re, html, unicodedata
# Importa sua função existente para consultar o teor (main.py)
try:
    from function import consultar_teor  # usa sua versão robusta
except Exception as e:
    consultar_teor = None

st.set_page_config(page_title="🧾 PJe Manifestador Automático", layout="centered")

st.title("🧾 Sistema de Envio Automático de Petições ao PJe")
st.markdown(
    """
Este aplicativo automatiza a entrega de manifestações processuais via API do PJe (TJPI).

⚠️ **Aviso importante:** O sistema **tomará ciência** dos expedientes para ler o conteúdo antes de realizar o protocolo da petição.
"""
)

# ================================
# Helpers
# ================================
'''essas funções comentadas permitem a busca pelas palavras digitadas em qualquer ordem no texto do expediente.'''
# def _normalizar(texto: str) -> str:
#     """Remove acentos, tags HTML e normaliza espaços"""
#     texto = html.unescape(texto)
#     texto = re.sub(r"<[^>]+>", " ", texto)
#     texto = unicodedata.normalize("NFD", texto)
#     texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")  # remove acentos
#     texto = re.sub(r"\s+", " ", texto).lower()
#     return texto.strip()


# def _buscar_expressao_no_conteudo(conteudo: str, expressao: str) -> bool:
#     """
#     Retorna True se TODAS as palavras digitadas na expressão
#     forem encontradas (em qualquer ordem) no texto.
#     Ex: "decisão rejeito embargos" → todas essas palavras devem estar no texto.
#     """
#     if not conteudo or not expressao:
#         return False

#     texto = _normalizar(conteudo)
#     termos = _normalizar(expressao).split()

#     # Verifica se todos os termos aparecem no texto
#     return all(termo in texto for termo in termos)
def _buscar_expressao_no_conteudo(conteudo: str, expressao: str) -> bool:
    if not conteudo:
        return False
    # Remove tags HTML e normaliza
    texto = re.sub(r"<[^>]+>", " ", html.unescape(conteudo))
    texto = re.sub(r"\s+", " ", texto).lower()
    termo = expressao.lower().strip()
    return termo in texto

def _to_base64(data_bytes: bytes) -> str:
    return base64.b64encode(data_bytes).decode("utf-8")

def _md5_hex(data_bytes: bytes) -> str:
    return hashlib.md5(data_bytes).hexdigest()

def _read_uploaded_file(uploaded_file):
    # Streamlit's UploadedFile -> bytes
    return uploaded_file.read()

def _endpoint_for_grau(grau: str) -> str:
    base = "https://pje.tjpi.jus.br"
    if "2" in grau:
        return f"{base}/2g/intercomunicacao?wsdl"
    return f"{base}/1g/intercomunicacao?wsdl"

def enviar_manifestacao_pje(cpf: str, senha: str, grau: str, numero_processo: str,
                            expediente: str | None, descricao: str,
                            p7s_bytes: bytes) -> str:
    """
    Monta e envia a requisição SOAP de 'entregarManifestacaoProcessual' usando
    as credenciais do usuário e o arquivo .p7s fornecido.
    Retorna o texto cru da resposta SOAP.
    """
    conteudo_base64 = _to_base64(p7s_bytes)
    pdf_hash = _md5_hex(p7s_bytes)
    data_envio = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "entregarManifestacaoProcessual",
    }

    # O PJe do TJPI aceita parâmetro opcional do expediente via tip:parametros
    parametros_xml = ""
    if expediente:
        parametros_xml = f'''
                <tip:parametros xmlns:tip="http://www.cnj.jus.br/tipos-servico-intercomunicacao-2.2.2"
                                nome="mni:idsProcessoParteExpediente"
                                valor="{expediente}"/>'''

    body = f'''<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
  <SOAP-ENV:Header/>
  <SOAP-ENV:Body>
    <ns5:entregarManifestacaoProcessual
        xmlns:ns2="http://www.cnj.jus.br/tipos-servico-intercomunicacao-2.2.2"
        xmlns:ns3="http://www.cnj.jus.br/intercomunicacao-2.2.2"
        xmlns:ns5="http://www.cnj.jus.br/servico-intercomunicacao-2.2.2/"
        xmlns:ns6="http://ws.pje.cnj.jus.br/">

      <ns2:idManifestante>{cpf}</ns2:idManifestante>
      <ns2:senhaManifestante>{senha}</ns2:senhaManifestante>
      <ns2:numeroProcesso>{numero_processo}</ns2:numeroProcesso>
{parametros_xml}
      <ns2:documento
          descricao="{html.escape(descricao)}"
          hash="{pdf_hash}"
          mimetype="application/pkcs7-signature"
          nivelSigilo="0"
          tipoDocumento="1000103">
        <ns3:conteudo>{conteudo_base64}</ns3:conteudo>
      </ns2:documento>
      <ns2:dataEnvio>{data_envio}</ns2:dataEnvio>
    </ns5:entregarManifestacaoProcessual>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>'''

    url = _endpoint_for_grau(grau)
    resp = requests.post(url, data=body.encode("utf-8"), headers=headers, timeout=120)
    return resp.text


def _obter_texto_do_teor(numero_processo: str, expediente: str) -> str | None:
    """
    Usa main.consultar_teor (se disponível) para obter o HTML/texto da comunicação.
    Se consultar_teor não estiver disponível, retorna None.
    """
    if consultar_teor is None:
        return None
    st.write("🔧 Chamando consultar_teor agora...")
    try:
        sucesso, payload = consultar_teor(numero_processo, expediente, cpf, senha, debug=True)
        st.write("🔧 Retorno:", sucesso)
        # a função pode retornar o próprio texto ou um caminho de arquivo .html
        if payload and isinstance(payload, str) and payload.lower().endswith(".html"):
            try:
                with open(payload, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                return None
        return payload if isinstance(payload, str) else None
    except Exception:
        st.write("não consegui consultar o teor do expediente")
        return None

# ================================
# Inputs do usuário
# ================================
st.subheader("🔐 Credenciais de Acesso ao PJe")
col1, col2 = st.columns(2)
with col1:
    cpf = st.text_input("CPF (login PJe)", placeholder="00000000000")
with col2:
    senha = st.text_input("Senha do PJe", type="password")

grau = st.selectbox("Selecione o grau de jurisdição:", ["1º Grau", "2º Grau"])

st.divider()

st.subheader("📂 Envio de Arquivos")
arquivo_planilha = st.file_uploader("📊 Planilha de processos (XLSX)", type=["xlsx"])
arquivo_peticao = st.file_uploader("📄 Petição assinada (.p7s)", type=["p7s"])

descricao_peticao = st.text_input("📝 Descrição da Petição", placeholder="Ex: Contrarrazões aos Embargos de Declaração")
expressao_busca = st.text_input(
    "🔍 Expressão/frase a buscar no expediente (dispara o protocolo)",
    placeholder="Ex: apresentar contrarrazões",
)

st.warning("Este sistema **tomará ciência** dos expedientes para ler o conteúdo antes de peticionar.", icon="⚠️")

executar = st.button("🚀 Iniciar Protocolo Automático", type="primary")

# ================================
# Execução
# ================================
if executar:
    if not all([cpf, senha, arquivo_planilha, arquivo_peticao, descricao_peticao, expressao_busca]):
        st.error("⚠️ Preencha todos os campos obrigatórios antes de iniciar.")
        st.stop()

    try:
        df = pd.read_excel(arquivo_planilha, engine="openpyxl")
    except Exception as e:
        st.error(f"Não foi possível ler a planilha enviada: {e}")
        st.stop()

    # Validação mínima das colunas esperadas
    col_proc = "Número do Processo"
    col_exp = "Expediente"
    if col_proc not in df.columns or col_exp not in df.columns:
        st.error(f"A planilha deve conter as colunas '{col_proc}' e '{col_exp}'.")
        st.stop()

    p7s_bytes = arquivo_peticao.read()

    resultados = []
    total = len(df)
    progresso = st.progress(0, text="Iniciando leitura dos processos...")

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        numero_processo = str(row[col_proc]).strip()
        expediente = str(row[col_exp]).strip()

        st.write(f"📂 **Processo {numero_processo}** — Expediente {expediente}")

        # Passo 1: consultar teor e verificar expressão
        conteudo = _obter_texto_do_teor(numero_processo, expediente)
        st.write("este é o texto obtido", conteudo)
        if conteudo and _buscar_expressao_no_conteudo(conteudo, expressao_busca):
            st.success("✅ Expressão encontrada no expediente. Enviando petição...")

            try:
                resposta = enviar_manifestacao_pje(
                    cpf=cpf,
                    senha=senha,
                    grau=grau,
                    numero_processo=numero_processo,
                    expediente=expediente,
                    descricao=descricao_peticao,
                    p7s_bytes=p7s_bytes,
                )

                # critério de sucesso
                sucesso = "Manifestação processual recebida com sucesso".lower() in resposta.lower()
                status = "Protocolada com sucesso" if sucesso else "Falha no protocolo"

                resultados.append({
                    "Número do Processo": numero_processo,
                    "Expediente": expediente,
                    "Descrição": descricao_peticao,
                    "Data/Hora Protocolo": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if sucesso else "-",
                    "Status": status,
                })

                if sucesso:
                    st.write("📘 Manifestação processual recebida com sucesso.")
                else:
                    st.warning("⚠️ A resposta da API não confirmou o protocolo.")

            except Exception as e:
                st.error(f"❌ Erro ao enviar a petição: {e}")
                resultados.append({
                    "Número do Processo": numero_processo,
                    "Expediente": expediente,
                    "Descrição": descricao_peticao,
                    "Data/Hora Protocolo": "-",
                    "Status": f"Erro: {e}",
                })

        else:
            st.warning("⚠️ Expressão não encontrada no expediente. Nenhum envio realizado.")
            resultados.append({
                "Número do Processo": numero_processo,
                "Expediente": expediente,
                "Descrição": descricao_peticao,
                "Data/Hora Protocolo": "-",
                "Status": "Sem correspondência",
            })

        progresso.progress(i/total, text=f"Processando ({i}/{total})")
        sleep(1.0)

    st.success("✅ Processamento concluído!")

    df_resultados = pd.DataFrame(resultados)
    st.dataframe(df_resultados, use_container_width=True)

    nome_saida = f"resultados_manifestacoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df_resultados.to_excel(nome_saida, index=False)

    with open(nome_saida, "rb") as f:
        st.download_button(
            "⬇️ Baixar Relatório Excel",
            data=f.read(),
            file_name=nome_saida,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.info("🔎 Dica: consulte os processos da lista para confirmar o protocolo no PJe.")
