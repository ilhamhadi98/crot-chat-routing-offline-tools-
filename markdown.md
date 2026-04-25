# Analisis Proyek: CROT (Chat Routing Offline Tools)

## 1. Ringkasan Eksekutif

**CROT** adalah aplikasi web canggih yang berfungsi sebagai pusat kendali (control panel) dan gateway untuk berinteraksi dengan berbagai model bahasa besar (Large Language Models - LLMs). 

Aplikasi ini memungkinkan pengguna untuk:
- **Merutekan (Routing)** permintaan chat ke berbagai penyedia LLM, baik yang berjalan secara lokal (seperti Ollama) maupun yang berbasis cloud (seperti Gemini dan OpenAI).
- **Mengelola (Manage)** penyedia LLM, termasuk API keys dan ketersediaan model.
- **Melacak (Track)** penggunaan token dan estimasi biaya secara terperinci per sesi dan per provider.
- **Memantau (Monitor)** kinerja sistem (CPU, RAM, GPU) secara real-time.
- **Berinteraksi** melalui antarmuka chat yang modern dan responsif yang mendukung input teks dan gambar (multimodal).

Proyek ini dibangun di atas fondasi yang kokoh menggunakan **Flask** untuk backend dan **JavaScript** murni untuk frontend, dengan database **SQLite** untuk portabilitas dan kemudahan penggunaan.

---

## 2. Arsitektur Infrastruktur

Infrastruktur proyek ini dirancang untuk menjadi ringan, modular, dan mandiri (self-contained).

### A. Komponen Utama

| Komponen            | Teknologi / File                                      | Deskripsi                                                                                                          |
| ------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Web Server**      | `app.py` (Flask)                                      | Inti dari aplikasi. Menyediakan API endpoints, logika bisnis, dan melayani file frontend.                          |
| **LLM Router**      | `litellm` (Library)                                   | Pustaka kunci yang menangani kompleksitas pengiriman permintaan ke berbagai API LLM dengan format yang seragam.   |
| **Database**        | `crot_engine.db` (SQLite)                             | Menyimpan semua data persisten: sesi, pesan, provider, statistik, dan basis pengetahuan RAG. Dipilih karena tanpa server dan portabel. |
| **Frontend UI**     | `templates/index.html`, `static/css/`, `static/js/` | Antarmuka pengguna berbasis web yang dinamis, dibangun dengan HTML, CSS, dan JavaScript modular tanpa framework eksternal. |
| **Lingkungan Python** | `litellm-env/` (Direktori)                            | Kemungkinan sebuah virtual environment Python yang berisi semua dependensi seperti Flask dan LiteLLM.               |

### B. Diagram Arsitektur Sederhana

```
+----------------------+     +----------------------+     +-------------------------+
|      Browser         |     |      Web Server      |     |     LLM Providers       |
| (HTML/CSS/JS)        |     |     (Flask)          |     | (Ollama, Gemini, OpenAI)|
+----------------------+     +----------------------+     +-------------------------+
        |                          ^    |    ^                        ^
        |-------(1. HTTP API)----->|    |    |                        |
        |                          |    |    |----(3. LLM Request)---->|
        |<------(2. Stream)--------|    |                             |
        |                          |    |<----(4. LLM Response)----|
        |                          v    v
        |                  +----------------+
        |                  | SQLite DB      |
        |                  | (crot_engine.db)|
        |                  +----------------+
        v
    Pengguna
```

---

## 3. Alur Bisnis & Fungsionalitas

Alur kerja utama aplikasi berpusat pada interaksi chat, dari input pengguna hingga respons dari LLM.

### A. Alur Interaksi Chat

1.  **Inisialisasi**: Pengguna membuka aplikasi di browser. JavaScript di frontend secara otomatis mengambil daftar provider, sesi sebelumnya, dan statistik sistem dari backend.
2.  **Pemilihan**: Pengguna memilih **Provider** (misalnya, `ollama`) dan **Model** (misalnya, `llama3:8b`) dari dropdown di sidebar.
3.  **Input Pengguna**: Pengguna mengetik pesan di kotak chat. Secara opsional, pengguna juga dapat melampirkan gambar, menjadikan permintaan tersebut multimodal.
4.  **Pengiriman**: Frontend mengirimkan data ke endpoint `/chat` di backend. Data ini mencakup:
    - Pesan saat ini dan gambar.
    - Riwayat percakapan dari sesi saat ini (untuk konteks).
    - Nama provider dan model yang dipilih.
    - ID Sesi untuk pelacakan.
5.  **Proses Backend**:
    - **RAG Sederhana**: Backend pertama-tama melakukan pencarian *full-text* di dalam tabel `rag_kb` di database SQLite untuk menemukan pesan relevan dari percakapan sebelumnya dan menambahkannya sebagai konteks sistem.
    - **Routing Cerdas**: Menggunakan `litellm`, backend memformat permintaan dan mengirimkannya ke LLM yang sesuai (misalnya, ke server Ollama lokal di `http://localhost:11434`).
    - **Streaming**: Backend tidak menunggu seluruh respons selesai. Segera setelah token pertama diterima dari LLM, token tersebut langsung di-stream kembali ke frontend menggunakan *Server-Sent Events* (SSE).
6.  **Tampilan Respons**: Frontend menerima aliran token dan menampilkannya secara *real-time* di UI, memberikan efek "mengetik" yang dinamis.
7.  **Finalisasi & Logging**: Setelah aliran selesai, backend menghitung metrik penting (jumlah token, waktu proses, estimasi biaya) dan:
    - Menyimpan pesan pengguna dan respons asisten ke dalam tabel `messages`.
    - Memperbarui total token dan biaya di tabel `sessions`.
    - Menambahkan respons asisten ke dalam tabel `rag_kb` untuk digunakan di masa depan.
    - Mengirim metrik final ke frontend untuk ditampilkan di bawah pesan.

### B. Fungsionalitas Pendukung

-   **Manajemen Provider**: Pengguna dapat menambahkan, menghapus, dan memeriksa status koneksi provider LLM melalui modal "Provider Management". Ini memungkinkan fleksibilitas untuk beralih antara model lokal dan cloud.
-   **Manajemen Sesi**: Setiap percakapan disimpan sebagai sesi. Pengguna dapat dengan mudah memuat ulang percakapan lama dari daftar sesi untuk melanjutkannya.
-   **Dasbor Statistik**: Panel statistik memberikan wawasan langsung tentang penggunaan sumber daya sistem dan akumulasi biaya/token, yang sangat berguna untuk mengelola sumber daya dan anggaran.

---
## 4. Kesimpulan dan Potensi Pengembangan

**CROT** adalah sebuah alat yang sangat kuat dan fleksibel, berfungsi sebagai jembatan antara pengguna dan dunia LLM yang kompleks. Arsitekturnya yang ringan membuatnya mudah dijalankan di hampir semua mesin.

**Potensi Pengembangan di Masa Depan:**
- **Peningkatan RAG**: Mengintegrasikan dengan sistem RAG yang lebih canggih, seperti menggunakan embedding vectors dan database vektor untuk pencarian konteks yang lebih akurat.
- **Dukungan Agen (Agents)**: Menambahkan fungsionalitas agen di mana LLM dapat diberikan alat (tools) untuk berinteraksi dengan sistem eksternal.
- **Antrian Pekerjaan (Job Queue)**: Untuk tugas-tugas yang berjalan lama, sistem antrian seperti Celery dengan Redis dapat diimplementasikan.
- **UI yang Lebih Kaya**: Menambahkan fitur seperti folder untuk sesi, pencarian di dalam riwayat chat, dan visualisasi data statistik yang lebih interaktif.
