# MangaLens

*(English version below | Türkçe sürümü aşağıdadır)*

---

## 🇬🇧 ENGLISH

A real-time English to Turkish manga translation overlay for Windows.

Select speech bubbles or text on your screen with your mouse to instantly see the Turkish translation. The app runs quietly in the background and does not interrupt your reading experience.

### ✨ Features
- **Easy to Use:** Simply draw around the text with your mouse.
- **Smart Translation:** Uses Gemini AI to provide natural, meaning-focused translations rather than word-for-word.
- **Secure:** Screenshots are processed only in memory and are never saved to your computer.

### 📋 Requirements
- Windows 10 or 11 (64-bit)
- Python 3.10 or higher
- Google Gemini API Key (available for free at [aistudio.google.com](https://aistudio.google.com))

### 🚀 Installation & Running

1. Download the project to your computer and open the command line in the folder.
2. Type the following command to install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the following command to start the app (or double-click the `MangaLens Start.vbs` file in the folder):
   ```bash
   python main.py
   ```

On the first launch, you will be prompted to enter your Gemini API key. Enter and save it. The app will start running in the system tray (bottom right corner). The app is ready when you see a thin gold line around the edges of your screen.

### 💡 How to Use?
1. **Prepare to Select:** Right-click anywhere on the screen.
2. **Draw:** Left-click and hold to draw around the text you want to translate.
3. **Translate:** Release the left click to start the translation. It will appear in a small box following your mouse within a few seconds.
4. **Dismiss:** Left-click anywhere to remove the translation from the screen.

*You can right-click the MangaLens icon in the system tray (bottom right corner) to change settings, switch to a different model, or exit the app.*

---

## 🇹🇷 TÜRKÇE

Windows için ekran üzerinde çalışan, gerçek zamanlı İngilizce-Türkçe manga çeviri aracı.

Ekranda okuduğunuz mangadaki konuşma balonlarını veya metinleri farenizle seçerek anında Türkçe çevirisini görebilirsiniz. Uygulama arka planda sessizce çalışır ve okuma deneyiminizi bölmez.

### ✨ Özellikler
- **Kolay Kullanım:** Farenizle metnin etrafını çizmeniz yeterlidir.
- **Akıllı Çeviri:** Gemini yapay zekası sayesinde kelimesi kelimesine değil, anlama odaklı ve doğal bir çeviri sunar.
- **Güvenli:** Ekran görüntüleri sadece o anlık işlenir ve bilgisayarınıza kesinlikle kaydedilmez.

### 📋 Gereksinimler
- Windows 10 veya 11 (64-bit)
- Python 3.10 ve üzeri
- Google Gemini API Anahtarı ([aistudio.google.com](https://aistudio.google.com) adresinden ücretsiz alınabilir)

### 🚀 Kurulum ve Çalıştırma

1. Projeyi bilgisayarınıza indirin ve klasörün içinde komut satırını açın.
2. Gerekli kütüphaneleri kurmak için komut satırına şunu yazın:
   ```bash
   pip install -r requirements.txt
   ```
3. Uygulamayı başlatmak için şu komutu çalıştırın (veya klasördeki `MangaLens Start.vbs` dosyasına çift tıklayın):
   ```bash
   python main.py
   ```

İlk açılışta sizden Gemini API anahtarınızı girmeniz istenecektir. Anahtarı girip test ettikten sonra kaydedin. Uygulama sistem tepsisinde (sağ alt köşe) çalışmaya başlayacaktır. Ekranın kenarlarında ince sarı bir çizgi gördüğünüzde uygulama hazır demektir.

### 💡 Nasıl Kullanılır?
1. **Seçime Hazırlanma:** Ekranda herhangi bir yere sağ tıklayın.
2. **Çizim:** Çevirmek istediğiniz metnin etrafını sol tıklayıp basılı tutarak çizin.
3. **Çeviri:** Sol tıklamayı bıraktığınızda çeviri başlar ve birkaç saniye içinde farenizi takip eden bir kutucukta belirir.
4. **Kapatma:** Çeviriyi ekrandan kaldırmak için herhangi bir yere sol tıklamanız yeterlidir.

*Ayarları değiştirmek, farklı bir modele geçmek veya uygulamadan çıkmak için sistem tepsisindeki (sağ alt köşedeki) MangaLens simgesine sağ tıklayabilirsiniz.*
