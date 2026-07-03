from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import os
import json

app = Flask(__name__)
STATIC_DIR = os.path.join(app.root_path, "static")
ETF_FILE = os.path.join(app.root_path, "etfs.json")

PERIODOS = {
    "1m": "1mo",
    "6m": "6mo",
    "1y": "1y",
    "5y": "5y"
}

# -----------------------------
# Carregar ETFs do ficheiro JSON
# -----------------------------
def carregar_etfs():
    try:
        with open(ETF_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print("Erro ao carregar JSON:", e)
        return {}

# -----------------------------
# Guardar ETFs no ficheiro JSON
# -----------------------------
def guardar_etfs(etfs):
    with open(ETF_FILE, "w") as f:
        json.dump(etfs, f, indent=4)


# -----------------------------
# Gerar gráficos matplotlib
# -----------------------------
def gerar_graficos(etfs, periodo):
    raw = yf.download(etfs, period=periodo)

    if raw.empty:
        return False

    # Extrair apenas Close — robusto
    if isinstance(raw.columns, pd.MultiIndex):
        data = pd.DataFrame({ticker: raw["Close"][ticker] for ticker in etfs})
    else:
        raw.columns = [c[1] if isinstance(c, tuple) else c for c in raw.columns]
        data = raw.filter(etfs)

    data = data.loc[:, ~data.columns.duplicated()]

    if len(data) == 0:
        return False

    # Gráfico 1 — Preços
    plt.figure(figsize=(12, 6))
    for ticker in data.columns:
        plt.plot(data.index, data[ticker], label=ticker)
    plt.title(f"Comparação de Preços — {periodo}")
    plt.xlabel("Data")
    plt.ylabel("Preço")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(STATIC_DIR, "comparacao_precos.png"))
    plt.close()

    # Gráfico 2 — Retornos
    returns = data / data.iloc[0] * 100
    plt.figure(figsize=(12, 6))
    for ticker in returns.columns:
        plt.plot(returns.index, returns[ticker], label=ticker)
    plt.title(f"Retorno Percentual — {periodo}")
    plt.xlabel("Data")
    plt.ylabel("Retorno (%)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(STATIC_DIR, "comparacao_retornos.png"))
    plt.close()

    return True


# -----------------------------
# Rotas Flask
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    etfs_info = carregar_etfs()

    if request.method == "POST":
        etfs = request.form.getlist("etfs")
        periodo = request.form.get("periodo")

        if not etfs:
            return render_template("index.html", etf_info=etfs_info, periodos=PERIODOS,
                                   error="Selecione pelo menos um ETF.")

        ok = gerar_graficos(etfs, PERIODOS[periodo])

        if not ok:
            return render_template("index.html", etf_info=etfs_info, periodos=PERIODOS,
                                   error="Erro ao descarregar dados dos ETFs.")

        return render_template("dashboard.html",
                               etfs=etfs,
                               periodo=periodo,
                               etf_info=etfs_info)

    return render_template("index.html", etf_info=etfs_info, periodos=PERIODOS)


@app.route("/add", methods=["GET", "POST"])
def adicionar_etf():
    etfs_info = carregar_etfs()

    if request.method == "POST":
        novo_ticker = request.form.get("ticker").upper().strip()
        descricao = request.form.get("descricao").strip()

        if not novo_ticker or not descricao:
            return render_template("add.html", error="Preencha todos os campos.", etf_info=etfs_info)

        # Validar ticker no Yahoo Finance
        teste = yf.Ticker(novo_ticker).history(period="1mo")
        if teste.empty:
            return render_template("add.html", error="Ticker inválido ou sem dados.", etf_info=etfs_info)

        # Adicionar ao JSON
        etfs_info[novo_ticker] = descricao
        guardar_etfs(etfs_info)

        return render_template("add.html", sucesso=f"{novo_ticker} adicionado com sucesso!", etf_info=etfs_info)

    return render_template("add.html", etf_info=etfs_info)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

