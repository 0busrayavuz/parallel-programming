# Canlı Kenar Analitiği (RT Edge Live)

**Amaç:** Kamera veya video akışında kenar / görüntü analitiği yapıp aynı iş yükünü **sıralı**, **çok süreçli paralel** ve isteğe bağlı **bölünmüş ekran** üzerinden karşılaştırmak; süre, kare sayısı ve throughput gibi ölçüleri **JSON** ve isteğe bağlı **Markdown** ile kaydetmek.

**Teknoloji:** Python 3.10+, **OpenCV**, **NumPy**; paralel modda **`multiprocessing`** (`spawn`) ile okuyucu + işçi süreçleri; split ekranda sağ tarafta **`ThreadPoolExecutor`** (iş parçacığı havuzu). Giriş: `python -m rt_edge_live`.

---

## Gereksinimler

- Windows 10/11 (geliştirme ortamı), Python **3.10+**
- Bağımlılıklar: `requirements.txt` (`opencv-python`, `numpy`)

---

## Kurulum

```powershell
python -m pip install -r requirements.txt
```

---

## Örnek akış (önce kayıt, sonra tek JSON)

1. Split-screen ile işlenmiş görüntüyü videoya yazın (**q** veya **Ctrl+C** ile çıkın).  
2. Aynı video üzerinde `--metrics-split-out` ile önce sıralı, sonra tam paralel koşuyu çalıştırın; çıktı **`split.json`** içinde **`seq_split`** / **`par_split`** alanlarında toplanır.

```powershell
python -m rt_edge_live --source 0 --mode split-screen --workers 4 --profile standard --record split.mp4

python -m rt_edge_live --source .\split.mp4 --metrics-split-out split.json --max-frames 500 --no-window --profile stress --workers 4 --log-level WARNING
```

Kaynak, kare sınırı, profil ve `--workers` değerlerini kendi deneyinize göre değiştirin. Tüm bayraklar ve diğer örnekler için:

```powershell
python -m rt_edge_live --help
```

---

## Notlar

- Kaynak kodu **UTF-8** tutun. Metrik dosyası için PowerShell’de **`>`** yerine **`--metrics-out`** veya **`--metrics-split-out`** kullanın (UTF-16 riski).
- Ürün adı kodda ASCII olarak `Canli Kenar Analitigi` geçer; sürüm `rt_edge_live/version.py` içindeki `__version__` alanındadır.
