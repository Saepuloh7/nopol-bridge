# nopol-wrapper

Userbot Telegram yang membungkus @nopol_robot jadi HTTP lokal. Middleware (vehicle-api) memanggilnya dari belakang, lalu mengekspos ke luar dengan API key sendiri.

## Setup (Linux server — sekali)

```bash
git clone https://github.com/Saepuloh7/nopol-bridge.git
cd nopol-bridge
python3 -m pip install --user telethon || python3 -m pip install --user --break-system-packages telethon
python3 nopolbot.py --selfcheck   # harus: SELFCHECK PASS
```

Siapkan `api_id` + `api_hash` di https://my.telegram.org (App configuration). Jangan dibagikan.

## Jalan

```bash
export TG_API_ID=<angka>
export TG_API_HASH=<hex32>
python3 nopolbot.py
```

Login pertama (di terminal yang terlihat): nomor `+62...`, kode dari Telegram, 2FA bila aktif. Sesi disimpan `nopol_session.session` — login ulang tidak perlu selama file itu ada. **Jangan commit/unggah file `.session`** (sudah di .gitignore).

Setelah login sukses, jalankan permanen:

```bash
nohup python3 nopolbot.py > nopol.log 2>&1 &
```

## Endpoint (bind 127.0.0.1:8765)

| Endpoint | Kirim ke bot |
|---|---|
| `GET /nopul?nopol=AD1337AD` | `/nopul AD1337AD` |
| `GET /noka?rangka=NOMOR_RANGKA` | `/noka NOMOR_RANGKA` |
| `GET /nosin?mesin=NOMOR_MESIN` | `/nosin NOMOR_MESIN` |
| `GET /nik?nik=16DIGIT` | `/nik 16DIGIT` (wajib 16 digit) |
| `GET /nama?nama=NAMA` | `/nama NAMA` |
| `GET /send?text=...` | teks mentah apa pun |
| `GET /health` | — (cek koneksi) |

- Respon: `{"ok": true, "reply": "<balasan bot>"}`
- 400 = parameter salah; 502 = bot error; 504 = timeout (default 60s, `TG_TIMEOUT`)
- Port default 8765 (`NOPOL_PORT`)

## Integrasi middleware

Route di vehicle-api: terima request ber-API-key -> panggil `127.0.0.1:8765/send?text=...` -> kembalikan JSON. Jangan expose port 8765 ke publik (bind 127.0.0.1).

## Catatan

- Antrean serial (satu request per waktu) karena balasan bot tidak membawa ID korelasi.
- Hanya teks/caption diambil; balasan foto murni -> `reply` null.
- Userbot = akun pribadi, di luar izin resmi Telegram Bot API. Risiko ban kecil; jangan spam, hormati rate limit bot.
