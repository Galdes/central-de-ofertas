# Central de Ofertas

Feed público com as ofertas de Amazon, Shopee e Mercado Livre coletadas pelo bot
[amazon-telegram](https://github.com/Galdes/amazon-telegram) — enquanto o Telegram só
manda o top 5 de cada rodada, aqui fica tudo que foi coletado nos últimos dias.

Site estático (Astro), sem backend próprio: uma GitHub Action lê a planilha do Google
Sheets a cada hora, gera `src/data/ofertas.json` e republica no GitHub Pages.

## Rodando localmente

```bash
npm install
pip install -r requirements.txt

# gera src/data/ofertas.json a partir da planilha real
GOOGLE_SHEET_ID=xxx GOOGLE_CREDENTIALS_FILE=google_credentials.json python scripts/export_ofertas.py

npm run dev
```

## Secrets necessários no GitHub (Settings → Secrets and variables → Actions)

- `GOOGLE_CREDENTIALS_JSON` — conteúdo inteiro do JSON da service account (a mesma usada
  no repositório do bot).
- `GOOGLE_SHEET_ID` — ID da planilha.

## Publicação

Settings → Pages → Source = **GitHub Actions**. O workflow
[`build-deploy.yml`](.github/workflows/build-deploy.yml) builda e publica sozinho, de
hora em hora (ou via "Run workflow" manual).
