<![CDATA[<div align="center">

# 🎯 RT Edge Live — Canlı Kenar Analitiği

**Gerçek zamanlı kenar algılama ve paralel programlama performans karşılaştırma aracı**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-1.24+-013243?style=for-the-badge&logo=numpy&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows_10/11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Version](https://img.shields.io/badge/Version-1.2.1-2ea44f?style=for-the-badge)

</div>

---

## 📋 İçindekiler

- [Proje Hakkında](#-proje-hakkında)
- [Özellikler](#-özellikler)
- [Mimari](#-mimari)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Çalışma Modları](#-çalışma-modları)
- [İşleme Profilleri](#-i̇şleme-profilleri)
- [Çıktı & Raporlama](#-çıktı--raporlama)
- [Proje Yapısı](#-proje-yapısı)
- [Lisans](#-lisans)

---

## 🎯 Proje Hakkında

**RT Edge Live**, kamera veya video akışı üzerinde OpenCV tabanlı kenar/görüntü analitiği yapıp aynı iş yükünü **sıralı (sequential)**, **çok süreçli paralel (multiprocessing)** ve **bölünmüş ekran (split-screen)** modlarında karşılaştırmaya olanak tanır.

Temel amaç, paralel programlama tekniklerinin gerçek zamanlı görüntü işleme üzerindeki performans etkisini **ölçülebilir metriklerle** ortaya koymaktır.

> 💡 **Motivasyon:** Sıralı ve paralel iş hatlarının throughput, kare/saniye ve duvar saati gibi ölçülerle somut karşılaştırmasını yapmak.

---

## ✨ Özellikler

| Özellik | Açıklama |
|---------|----------|
| 🔄 **3 Çalışma Modu** | Sequential, Parallel (multiprocessing), Split-Screen |
| 🎚️ **4 İşleme Profili** | Fast, Standard, Quality, Stress |
| 📊 **Metrik Sistemi** | JSON ve Markdown formatında detaylı performans raporları |
| 🎥 **Video Kaydı** | İşlenmiş çıktıyı MP4/AVI olarak kaydetme |
| 📺 **HUD Overlay** | Gerçek zamanlı FPS, profil ve kare bilgisi gösterimi |
| ⚡ **Spawn Context** | Windows uyumlu `multiprocessing.spawn` mimarisi |
| 🧵 **Thread Pool** | Split-screen modunda `ThreadPoolExecutor` entegrasyonu |

---

## 🏗 Mimari

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI (cli.py)                         │
│              argparse · mod seçimi · metrik akışı            │
└──────────────┬──────────────┬──────────────┬────────────────┘
               │              │              │
       ┌───────▼──────┐ ┌────▼─────┐ ┌──────▼───────┐
       │  Sequential  │ │ Parallel │ │ Split-Screen │
       │  (tek süreç) │ │  (spawn) │ │  (threads)   │
       └───────┬──────┘ └────┬─────┘ └──────┬───────┘
               │              │              │
               └──────────────┼──────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  EdgeInspection   │
                    │    Pipeline       │
                    │  (pipeline.py)    │
                    └─────────┬─────────┘
                              │
               ┌──────────────┼──────────────┐
               │              │              │
         ┌─────▼─────┐ ┌─────▼─────┐ ┌──────▼──────┐
         │   HUD     │ │ Recorder  │ │   Report    │
         │ Overlay   │ │ (MP4/AVI) │ │ (MD/JSON)   │
         └───────────┘ └───────────┘ └─────────────┘
```

**Paralel Mod Detayı:**
```
  Reader Process          Worker Processes (N)          Display Thread
  ┌───────────┐          ┌──────────────────┐          ┌────────────┐
  │ VideoCapture │──►  │ job_q ──► worker() │──►  │ result_q    │
  │ kare okuma  │ Queue  │ process_frame()  │ Queue  │ sıralı HUD │
  └───────────┘          └──────────────────┘          └────────────┘
```

---

## 🔧 Kurulum

### Gereksinimler

- **Python 3.10+**
- **Windows 10/11** (geliştirme ortamı)

### Adımlar

```powershell
# 1. Repoyu klonlayın
git clone https://github.com/0busrayavuz/parallel-programming.git
cd parallel-programming

# 2. (Opsiyonel) Sanal ortam oluşturun
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Bağımlılıkları yükleyin
python -m pip install -r requirements.txt
```

---

## 🚀 Kullanım

Uygulama modül olarak çalıştırılır:

```powershell
python -m rt_edge_live [BAYRAKLAR]
```

### Hızlı Başlangıç

```powershell
# Kamera ile paralel mod (varsayılan)
python -m rt_edge_live --source 0

# Video dosyası ile sıralı mod
python -m rt_edge_live --source demo.mp4 --mode sequential --profile standard

# Tüm bayrakları görmek için
python -m rt_edge_live --help
```

### Performans Karşılaştırma (Benchmark)

```powershell
# 1) Sıralı koşu — metrik JSON'a kaydet
python -m rt_edge_live --source demo.mp4 --mode sequential --max-frames 500 --no-window --metrics-out seq.json

# 2) Paralel koşu — metrik JSON'a kaydet
python -m rt_edge_live --source demo.mp4 --mode parallel --workers 4 --max-frames 500 --no-window --metrics-out par.json

# 3) İki JSON'u Markdown raporda karşılaştır
python -m rt_edge_live --compare-json seq.json par.json --report RAPOR.md
```

### Tek Komutla Çift Ölçüm (Split JSON)

```powershell
# Önce sıralı, sonra paralel koşuyu otomatik yapar; tek JSON çıktı
python -m rt_edge_live --source demo.mp4 --metrics-split-out split.json --max-frames 500 --no-window --profile stress --workers 4 --log-level WARNING
```

### Split-Screen (Bölünmüş Ekran) + Video Kaydı

```powershell
# Sol: seri | Sağ: ThreadPool — gerçek zamanlı karşılaştırma
python -m rt_edge_live --source 0 --mode split-screen --workers 4 --profile standard --record split.mp4
```

---

## 🔀 Çalışma Modları

| Mod | Komut | Mekanizma | Kullanım Amacı |
|-----|-------|-----------|----------------|
| **Sequential** | `--mode sequential` | Tek süreç, seri işleme | Temel performans (baseline) ölçümü |
| **Parallel** | `--mode parallel` | `multiprocessing.spawn` ile N işçi süreç | Gerçek çok çekirdekli paralellik |
| **Split-Screen** | `--mode split-screen` | Sol: seri · Sağ: `ThreadPoolExecutor` | Görsel yan yana karşılaştırma |

> ⚠️ **Not:** Split-screen modunda her iki taraf aynı CPU kaynaklarını paylaşır. Tam throughput karşılaştırması için `sequential` ve `parallel` modlarını ayrı koşularla `--metrics-out` ile kullanın.

---

## 🎚 İşleme Profilleri

Her profil, farklı ağırlıkta bir kenar algılama iş hattı tanımlar:

| Profil | Flag | Pipeline | Hedef |
|--------|------|----------|-------|
| **Fast** | `--profile fast` | GaussianBlur(5) → Canny | Düşük gecikme, hızlı önizleme |
| **Standard** | `--profile standard` | CLAHE → Gaussian(7) → Canny → Morfoloji → Overlay | Üretim standardı |
| **Quality** | `--profile quality` | CLAHE → BilateralFilter(9) → Canny → Morfoloji → Overlay | Yüksek doğruluk |
| **Stress** | `--profile stress` | CLAHE → MedianBlur(15) → 11× Gaussian(21) + Canny → NumPy patch | Ağır CPU — paralellik demosu |

> 💡 **Legacy uyumluluk:** `light` → `fast`, `balanced` → `standard`, `heavy` → `quality` alias'ları desteklenir.

---

## 📊 Çıktı & Raporlama

### JSON Metrikleri

```powershell
# Dosyaya yaz (UTF-8, önerilen)
--metrics-out results.json

# Çift ölçüm (seq + par tek JSON)
--metrics-split-out split.json

# Stdout'a tek satır JSON
--metrics-json
```

**Örnek JSON çıktısı:**
```json
{
  "product": "Canli Kenar Analitigi",
  "version": "1.2.1",
  "profile": "standard",
  "mode": "parallel",
  "workers": 4,
  "frames": 500,
  "wall_seconds": 12.345678,
  "throughput_frames_per_s": 40.5012
}
```

### Markdown Raporu

```powershell
# Tek koşu raporu
--report rapor.md

# İki JSON karşılaştırma raporu
--compare-json seq.json par.json --report KIYAS.md
```

### Video Kaydı

```powershell
# İşlenmiş kareleri MP4'e kaydet
--record cikti.mp4 --record-fps 30
```

> 📝 `mp4v` codec başarısız olursa otomatik olarak `MJPG` (AVI) formatına düşer.

---

## 📁 Proje Yapısı

```
paralel/
├── parallel_video.py          # Giriş shim (python parallel_video.py ...)
├── requirements.txt           # Bağımlılıklar (opencv-python, numpy)
├── README.md
│
└── rt_edge_live/              # Ana paket
    ├── __init__.py            # Paket tanımı & dışa aktarım
    ├── __main__.py            # python -m rt_edge_live desteği
    ├── cli.py                 # CLI argparse, mod yönlendirme, metrik akışı
    ├── runners.py             # 3 çalıştırıcı: sequential, parallel, split-screen
    ├── pipeline.py            # EdgeInspectionPipeline — 4 profil iş hattı
    ├── mp_workers.py          # multiprocessing okuyucu + işçi süreç hedefleri
    ├── display.py             # Paralel modda sıralı kare tüketimi + HUD
    ├── profiles.py            # Profil tanımları (fast/standard/quality/stress)
    ├── report.py              # Markdown rapor üretimi (tek koşu + karşılaştırma)
    ├── recorder.py            # VideoRecorder — MP4/AVI yazıcı (codec fallback)
    ├── metrics.py             # JSON benchmark payload oluşturma
    ├── hud.py                 # Üst bant overlay + rolling FPS tahmini
    ├── logging_setup.py       # Ana + alt süreç log yapılandırması
    ├── constants.py           # Ürün sabitleri
    ├── video_source.py        # Kaynak çözümlemesi (kamera indeksi / dosya yolu)
    └── version.py             # Sürüm bilgisi (1.2.1)
```

---

## 🔑 Temel CLI Bayrakları

| Bayrak | Varsayılan | Açıklama |
|--------|-----------|----------|
| `--source` | `0` | Kamera indeksi veya video dosya yolu |
| `--mode` | `parallel` | `sequential` · `parallel` · `split-screen` |
| `--workers` | CPU-1 | Paralel modda işçi süreç sayısı |
| `--profile` | `standard` | `fast` · `standard` · `quality` · `stress` |
| `--max-frames` | ∞ | N kare sonra dur |
| `--no-window` | `false` | Görüntü penceresi gösterme (benchmark için) |
| `--metrics-out` | — | Metrik JSON dosyasına yaz (UTF-8) |
| `--metrics-split-out` | — | Sıralı + paralel çift ölçüm tek JSON |
| `--record` | — | İşlenmiş videoyu MP4 olarak kaydet |
| `--report` | — | Markdown ölçüm raporu üret |
| `--compare-json` | — | İki JSON ölçümünü karşılaştır |
| `--benchmark` | `false` | İnsan okunur ölçüm özeti (stdout) |
| `--log-level` | `INFO` | `DEBUG` · `INFO` · `WARNING` · `ERROR` |

---

## 📝 Notlar

- Kaynak kodu **UTF-8** olarak tutun.
- Metrik dosyası için PowerShell'de `>` yerine `--metrics-out` veya `--metrics-split-out` kullanın (UTF-16 riski).
- Ürün adı kodda ASCII olarak `Canli Kenar Analitigi` geçer; sürüm `rt_edge_live/version.py` içindeki `__version__` alanındadır.

---

<div align="center">

**Büşra Yavuz** tarafından geliştirilmiştir.

</div>
]]>
