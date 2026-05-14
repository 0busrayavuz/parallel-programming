# RT Kenar Analitigi — Proje Rehberi

Bu depo, **Gercek zamanli paralel video isleme** odevi kapsaminda: tek video akisi, CPU uzerinde OpenCV ile goruntu isleme, `multiprocessing` isci havuzu, sirali veya bolunmus ekranda gosterim ile **olcum ve rapor** (JSON / Markdown) araclarini bir arada sunar. Paket girisi: `python -m rt_edge_live`.

## Olcum icin iki adim (komutlari bu sirayla calistirin)

1. **Kayit:** Kameradan (veya baska kaynaktan) split-screen gorunumuyle islenmis videoyu `split.mp4` olarak kaydedersiniz; durdurmak icin pencerede **q** (veya Ctrl+C).
2. **Metrik dosyasi:** Ayni `split.mp4` uzerinde once **sequential**, sonra **parallel** kosulari calisir; sonuc tek dosyada `seq_split` ve `par_split` alanlariyla `split.json` olarak yazilir.

Asagidaki iki satir **dosyada ozellikle tutulmus referans komutlardir**; pratikte once birini, bitince digerini ayni sira ile calistirin:

```powershell
python -m rt_edge_live --source 0 --mode split-screen --workers 4 --profile standard --record split.mp4

python -m rt_edge_live --source .\split.mp4 --metrics-split-out split.json --max-frames 500 --no-window --profile stress --workers 4 --log-level WARNING
```

Kaynak yolu (`0`, `.\split.mp4`), `--max-frames`, `--profile` ve `--workers` degerlerini kendi deneyinize gore degistirebilirsiniz.

## 1. Gereksinimler

- Windows 10/11 (gelistirme bu ortamda testlendi)
- Python 3.10+ (3.13 ile calisir)
- OpenCV + NumPy (`requirements.txt`)

## 2. Kurulum

Proje kok klasorunde (`paralel`):

```powershell
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

### Kameradan MP4 kayit

Islenmis goruntu (kenar analitigi uygulanmis) diske yazilir; **`--record` olmadan dosya olusmaz.**

```powershell
python -m rt_edge_live --source 0 --mode parallel --profile standard --record cikti.mp4
```

`--record-fps` ile FPS ayarlanir (varsayilan 30). Durdurmak icin yine **q**; kayit dosyasi `rec.close()` ile kapanir.

### Split-screen kiyas (`--mode split-screen`)

Ekran **dikey cizgiyle** ikiye bolunur: **sol** ayni kareyi **sequential** (`process_frame` ana is parcaciginda), **sag** ayni kareyi **ThreadPoolExecutor** (`--workers`) ile isler; her karede **aynı Frame ID** kullanilir.

- Sol ust: kirmizi **SEQUENTIAL** + tahmini FPS + seri sure (ms).
- Sag ust: yesil **PARALLEL** + tahmini FPS + havuz duvar suresi (ms) + `wait-after-seq` (latency).
- Altta: **Frame ID** ve tum kare icin **duvar FPS**.

**Onemli:** Sag taraftaki "PARALLEL" bu modda **iplik havuzudur**; tam `multiprocessing` (`--mode parallel`) tek pencerede her kare senkron maliyetli oldugundan split UI’da kullanilmaz. Gercek **spawn isci havuzu** throughput kiyasini yine `sequential` / `parallel` + `--metrics-out` ile yapin. Split modda iki is yuku ayni CPU’yu paylasir; log’da uyari ve yuksek duvar suresinde ek **WARNING** verilir — yan FPS’leri mutlak performans sanmayin.

```powershell
python -m rt_edge_live --source 0 --mode split-screen --workers 4 --profile standard --record split.mp4
```

Split kosusundan sonra **tek JSON + Markdown** (ekran ozeti + ortalama ms / tahmini FPS):

```powershell
python -m rt_edge_live --source 0 --mode split-screen --workers 4 --profile standard --max-frames 500 --no-window --metrics-out split.json --report SPLIT_RAPOR.md --log-level WARNING
```

`split.json` icinde `split_screen` anahtari altinda seri / parallel dal / bekleme ortalamalari yer alir; `SPLIT_RAPOR.md` ayni tabloyu insan okunur formatta yazar.

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
| `stress` | **Paralellik demasi:** buyuk cekirdek + tekrarli Gaussian/Canny + `medianBlur(15)`; IPC maliyetini gorme altinda birakmak icin |

Eski isimler: `light` -> `fast`, `balanced` -> `standard`, `heavy` -> `quality`

### Paralel kiyas icin agir yuk (`--profile stress`)

Hafif profillerde (`standard`) is cok hizli biter; isci surecler arasi **pickle / kuyruk** maliyeti baskin cikabilir. **`stress`** profili kare basina cok daha fazla CPU harcar; boylece **parallel** modun **sequential**e gore hizlanmasi gercekci sekilde gorulebilir.

```powershell
python -m rt_edge_live --source .\video.mp4 --mode sequential --profile stress --max-frames 200 --no-window --metrics-out seq_stress.json --log-level WARNING
python -m rt_edge_live --source .\video.mp4 --mode parallel --profile stress --workers 4 --max-frames 200 --no-window --metrics-out par_stress.json --log-level WARNING
python -m rt_edge_live --compare-json seq_stress.json par_stress.json --report KIYAS_STRESS.md --log-level WARNING
```

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

Iki **ayri kosudan** (`sequential` ve `parallel`) uretilen JSON dosyalari:

```powershell
python -m rt_edge_live --compare-json seq.json par.json --report KIYAS.md --log-level WARNING
```

### Ayni kaynak: seri + paralel tek JSON (`split.json`)

`seq_split.json` ve `par_split.json` ayri ayri uretmek yerine, ayni kosullarda once **sequential** sonra **parallel** calisir; cikti tek dosyada `seq_split` ve `par_split` anahtarlariyla gelir (`--mode` bu akista yok sayilir; `--metrics-out` ile birlikte kullanilamaz).

```powershell
python -m rt_edge_live --source .\split.mp4 --metrics-split-out split.json --max-frames 500 --no-window --profile stress --workers 4 --log-level WARNING
```

Istege bagli `--report KIYAS.md` ile Markdown kiyaslama da yazilir.

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

**Split-screen:** tek surecte okuma; her kare sol seri, sag `ThreadPoolExecutor` ile (UI kiyas); tam `multiprocessing` ayri `--mode parallel`.

## 6. Klasor yapisi

| Yol | Rol |
|-----|-----|
| `rt_edge_live/` | Ana paket |
| `rt_edge_live/cli.py` | CLI, olcum, rapor tetikleme |
| `rt_edge_live/pipeline.py` | Goruntu is hatti |
| `rt_edge_live/mp_workers.py` | `reader`, `worker` |
| `rt_edge_live/display.py` | Sirali tuketim + HUD |
| `rt_edge_live/runners.py` | `run_parallel`, `run_sequential`, `run_split_screen_compare` |
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