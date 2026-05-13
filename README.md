# RT Kenar Analitigi — Proje Rehberi

Bu depo, "Gercek Zamanli Paralel Video Isleme" odevi icin: tek video akisi, CPU uzerinde `multiprocessing` isci havuzu, sirali gosterim ve olcum/rapor araclarini icerir.

## 1. Gereksinimler

- Windows 10/11 (gelistirme bu ortamda testlendi)
- Python 3.10+ (3.13 ile calisir)
- OpenCV + NumPy (`requirements.txt`)

## 2. Kurulum

Proje kok klasorunde (`paralel`):

```powershell
cd C:\Users\busra\paralel
python -m pip install -r requirements.txt
```

## 3. Calistirma (onemli komutlar)

### Temel

```powershell
python -m rt_edge_live --help
```

Kamera (varsayilan kaynak `0`), paralel, standart profil:

```powershell
python -m rt_edge_live --source 0 --mode parallel --profile standard
```

Video dosyasi:

```powershell
python -m rt_edge_live --source demo.mp4 --mode parallel --profile standard
```

Pencereden cikis: **q**

### Eski giris (kokteki sarici)

```powershell
python parallel_video.py --source demo.mp4 --mode parallel --profile standard
```

### Profiller

| Profil | Aciklama |
|--------|----------|
| `fast` | Dusuk gecikme |
| `standard` | Varsayilan (CLAHE + kenar + overlay) |
| `quality` | Daha agir is (bilateral vb.) |

Eski isimler: `light` -> `fast`, `balanced` -> `standard`, `heavy` -> `quality`

### Olcum (odev tablosu icin)

**Onerilen:** Metrikleri dosyaya UTF-8 yaz (`>` yerine):

```powershell
python -m rt_edge_live --source demo.mp4 --mode sequential --profile standard --max-frames 500 --no-window --metrics-out seq.json --log-level WARNING

python -m rt_edge_live --source demo.mp4 --mode parallel --workers 4 --profile standard --max-frames 500 --no-window --metrics-out par.json --log-level WARNING
```

Konsola tek satir JSON:

```powershell
python -m rt_edge_live --source demo.mp4 --max-frames 100 --no-window --metrics-json
```

Insan okunur ozet:

```powershell
python -m rt_edge_live --source demo.mp4 --max-frames 500 --no-window --benchmark
```

### Karsilastirma raporu (Markdown)

```powershell
python -m rt_edge_live --compare-json seq.json par.json --report KIYAS.md --log-level WARNING
```

### Video kayit

```powershell
python -m rt_edge_live --source demo.mp4 --max-frames 300 --record cikti.mp4 --record-fps 30
```

`mp4v` acilmazsa ayni klasorde `*_rec.avi` (MJPG) denenebilir.

### Tek kosuda rapor + olcum

```powershell
python -m rt_edge_live --source demo.mp4 --max-frames 200 --no-window --report rapor.md --benchmark
```

## 4. Kaynak kodlama (onemli)

Python dosyalarini **UTF-8** kaydedin. UTF-16 ile kaydedilirse `SyntaxError: null bytes` gorulebilir.

PowerShell ile `>` kullanirsaniz JSON dosyasi UTF-16 olabilir; `--metrics-out` kullanin veya `report.py` coklu kodlamayi okur.

## 5. Mimari (kisa)

1. **Okuyucu surec:** kareleri okur, is kuyruguna `(id, kare)` koyar.
2. **Isci surecler:** `process_frame` / `EdgeInspectionPipeline` ile isler, sonuc kuyruguna yazar.
3. **Ana surec:** sonuclari kare numarasina gore siralar, HUD, istege bagli `imshow` ve `VideoRecorder`.

Siralı mod: ayni hat tek surecte (kiyaslama).

## 6. Klasor yapisi

| Yol | Rol |
|-----|-----|
| `rt_edge_live/` | Ana paket |
| `rt_edge_live/cli.py` | CLI, olcum, rapor tetikleme |
| `rt_edge_live/pipeline.py` | Goruntu is hatti |
| `rt_edge_live/mp_workers.py` | `reader`, `worker` |
| `rt_edge_live/display.py` | Sirali tuketim + HUD |
| `rt_edge_live/runners.py` | `run_parallel`, `run_sequential` |
| `rt_edge_live/recorder.py` | Video yazici |
| `rt_edge_live/report.py` | Markdown rapor, JSON okuma |
| `rt_edge_live/metrics.py` | JSON yuku |
| `parallel_video.py` | `python parallel_video.py` uyumlulugu |

## 7. Ust seviye icin gelistirme fikirleri (yol haritasi)

Asagidakiler projeyi akademik ve muhendislik olarak yukseltir; hepsini yapmak zorunlu degil.

### Olcum ve guvenilirlik

- **Islem suresi ayrıştırma:** `process_frame` ic suresi vs kuyruk bekleme vs `imshow` (timestamp ile).
- **Gecikme (latency):** kare uretim zamani ile gosterim zamani farki (p99).
- **Otomatik tekrar:** ayni komutu N kez calistirip ortalama / standart sapma.

### Performans

- **GPU dali (opsiyonel):** OpenCV `cuda` veya PyTorch ile kenar/islem; CPU havuzu ile kiyas bolumu.
- **Kare seritlerine bolme:** tek kareyi yatay seritlere bolup paralel (uzamsal paralellik).
- **Zero-copy / paylasilan bellek:** buyuk karelerde kopyayi azaltma (ileri duzey).

### Urun ve operasyon

- **YAML/JSON config** dosyasi (profil parametreleri, kuyruk boyutu).
- **Yapilandirilmis log** (JSON satirlari) + log seviyesi.
- **CI:** `py_compile`, kisa `--max-frames` smoke test.

### Goruntu ve rapor

- **HTML rapor** (graf: workers vs throughput).
- **Kaynak FPS otomatik:** `CAP_PROP_FPS` ile `--record-fps` onerisi.
- **Unit test:** `canonical_profile`, JSON rapor parser.

### Guvenlik ve dayaniklilik

- **Maksimum cozunurluk** limiti, bellek koruma.
- **Hata durumunda** okuyucu/isci temiz kapanis (zaten temel var; genisletilebilir).

---

*Surum: `rt_edge_live/version.py` icindeki `__version__`.*