# ⚖️ PJE Manifestador – Automação de Petições Avulsas (PGE-PI)

Aplicativo desenvolvido para automatizar o envio em lote de **petições avulsas** ao sistema **PJe (TJPI)**, por meio da API oficial de interoperabilidade do CNJ.  
Desenvolvido no âmbito da **Procuradoria-Geral do Estado do Piauí (PGE-PI)**, o sistema visa otimizar o trabalho dos procuradores na juntada de manifestações repetitivas (como contrarrazões e embargos).

---

## 🧭 Objetivo

O sistema permite:

- Realizar login no PJe com CPF e senha do procurador;
- Ler automaticamente o teor dos expedientes pendentes;
- Identificar expressões pré-definidas (ex.: “apresentar contrarrazões”, “rejeito embargos”);
- Protocolar automaticamente as petições **assinadas digitalmente (.p7s)**;
- Gerar um relatório final em Excel com o status de cada protocolo.

---

## ⚙️ Pré-requisitos

1. **Python 3.10+**  
2. **Bibliotecas necessárias** (instale via `pip`):
   ```bash
   pip install streamlit requests pandas openpyxl reportlab
