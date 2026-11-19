# nopol-wrapper

Userbot Telegram yang membungkus @nopol_robot jadi HTTP lokal. Middleware (vehicle-api) memanggilnya dari belakang, lalu mengekspos ke luar dengan API key sendiri.

## Setup (sekali)

```bash
cd C:/Users/User/nopol-wrapper
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

Siapkan `api_id` + `api_hash` di https://my.telegram.org (App configuration). Jangan dibagikan.

## Jalan

```bash
export TG_API_ID=123456
export TG_API_HASH=abcdef1234567890abcdef1234567890
.venv/Scripts/python nopolbot.py
```

Login pertama (di terminal yang terlihat): nomor `+62...`, kode dari Telegram, 2FA bila aktif. Sesi disimpan `nopol_session.session` — login ulang tidak perlu selama file itu ada. **Jangan commit/unggah file `.session`** (sudah di .gitignore).

## Pakai

```bash
curl "http://127.0.0.1:8765/send?text=B+1234+XYZ"
# {"ok": true, "reply": "<balasan bot>"}
```

- `GET /health` — cek koneksi
- 400 = parameter `text` kosong; 502 = bot error; 504 = timeout (default 60s, set `TG_TIMEOUT`)
- Port default 8765 (`NOPOL_PORT`)

## Integrasi middleware

Route di vehicle-api: terima request ber-API-key -> panggil `127.0.0.1:8765/send?text=...` -> kembalikan JSON. Jangan expose port 8765 ke publik (bind 127.0.0.1).

## Catatan

- Antrean serial (satu request per waktu) karena balasan bot tidak membawa ID korelasi.
- Hanya teks/caption diambil; balasan foto murni -> `reply` null.
- Userbot = akun pribadi, di luar izin resmi Telegram Bot API. Risiko ban kecil; jangan spam, hormati rate limit bot.
