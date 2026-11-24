"""Materi belajar dan kuis untuk 24 skill awal. Jawaban benar HANYA ada di server (tidak pernah dikirim ke browser).
Format opsi: "English||Indonesia" bila perlu diterjemahkan; tanpa '||' berarti sama di dua bahasa.
quiz item: (pertanyaan_en, pertanyaan_id, [opsi], index_benar, alasan_en, alasan_id)"""

L = {}
def add(skill, goal, steps, practice, quiz): L[skill] = {"goal": goal, "steps": steps, "practice": practice, "quiz": quiz}

add("Networking basics",
 ("Understand how devices find and talk to each other on a network.", "Memahami bagaimana perangkat saling menemukan dan berkomunikasi di jaringan."),
 [("Learn what an IP address, subnet mask and gateway are, and write one example of each.", "Pelajari apa itu IP address, subnet mask, dan gateway, lalu tulis satu contoh masing-masing."),
  ("Learn the OSI layers (7) and name one device or protocol for each of layers 1 to 4.", "Pelajari 7 lapisan OSI dan sebutkan satu perangkat atau protokol untuk lapisan 1 sampai 4."),
  ("Open a command line, run ipconfig (Windows) or ip a (Linux), and find your own IP address and gateway.", "Buka command line, jalankan ipconfig (Windows) atau ip a (Linux), lalu temukan IP address dan gateway milikmu.")],
 ("Run ping to your gateway and to 8.8.8.8, then write what the results tell you.", "Jalankan ping ke gateway dan ke 8.8.8.8, lalu tulis apa arti hasilnya."),
 [("Which device connects different networks and forwards packets between them?", "Perangkat apa yang menghubungkan jaringan berbeda dan meneruskan paket di antaranya?", ["Router", "Hub", "Repeater"], 0, "A router works at layer 3 and forwards packets between networks.", "Router bekerja di lapisan 3 dan meneruskan paket antar jaringan."),
  ("How many bits are in an IPv4 address?", "Berapa bit panjang sebuah alamat IPv4?", ["16", "32", "64"], 1, "IPv4 uses 32 bits, written as four numbers from 0 to 255.", "IPv4 memakai 32 bit, ditulis sebagai empat angka 0 sampai 255."),
  ("Which protocol turns a website name into an IP address?", "Protokol apa yang mengubah nama situs menjadi IP address?", ["DNS", "DHCP", "ARP"], 0, "DNS translates names to IP addresses.", "DNS menerjemahkan nama menjadi IP address.")])

add("Routing & switching",
 ("Know how a switch and a router decide where data goes.", "Memahami bagaimana switch dan router menentukan ke mana data dikirim."),
 [("Learn what a MAC address table is and how a switch fills it.", "Pelajari apa itu tabel MAC address dan bagaimana switch mengisinya."),
  ("Learn what a VLAN is and why a school might use separate VLANs.", "Pelajari apa itu VLAN dan mengapa sekolah bisa memakai VLAN terpisah."),
  ("Learn the difference between static and dynamic routing.", "Pelajari beda routing statis dan dinamis.")],
 ("Draw a small network with 1 router and 2 switches on paper and mark which device uses MAC and which uses IP.", "Gambar jaringan kecil dengan 1 router dan 2 switch di kertas, lalu tandai perangkat mana yang memakai MAC dan mana yang memakai IP."),
 [("A switch forwards frames using which address?", "Switch meneruskan frame berdasarkan alamat apa?", ["IP address", "MAC address", "Port number"], 1, "Switches work at layer 2 with MAC addresses.", "Switch bekerja di lapisan 2 dengan MAC address."),
  ("What does a VLAN do?", "Apa fungsi VLAN?", ["Splits one switch into separate logical networks||Membagi satu switch menjadi beberapa jaringan logis terpisah", "Makes Wi-Fi faster||Membuat Wi-Fi lebih cepat", "Encrypts all traffic||Mengenkripsi semua lalu lintas"], 0, "VLANs separate broadcast domains.", "VLAN memisahkan broadcast domain."),
  ("Which is a dynamic routing protocol?", "Mana yang merupakan protokol routing dinamis?", ["OSPF", "DNS", "HTTP"], 0, "OSPF exchanges routes automatically between routers.", "OSPF bertukar rute otomatis antar router.")])

add("Mikrotik",
 ("Do basic setup of a MikroTik router with WinBox.", "Melakukan pengaturan dasar router MikroTik dengan WinBox."),
 [("Learn what RouterOS and WinBox are and how to connect to a router by MAC address.", "Pelajari apa itu RouterOS dan WinBox, dan cara terhubung ke router lewat MAC address."),
  ("Learn how to set an IP address on an interface and add a default route.", "Pelajari cara memberi IP address pada interface dan menambah default route."),
  ("Learn what NAT masquerade does and why a home network needs it.", "Pelajari fungsi NAT masquerade dan mengapa jaringan rumah membutuhkannya.")],
 ("In a simulator or lab router: set the LAN IP, add a DHCP server and a masquerade rule, then test internet access from a client.", "Di simulator atau router lab: atur IP LAN, tambahkan DHCP server dan aturan masquerade, lalu uji akses internet dari klien."),
 [("Which tool is the usual graphical program to manage a MikroTik router?", "Aplikasi grafis apa yang umum dipakai untuk mengatur router MikroTik?", ["WinBox", "Wireshark", "PuTTY only||Hanya PuTTY"], 0, "WinBox is MikroTik's own management tool.", "WinBox adalah aplikasi pengelola resmi MikroTik."),
  ("What does NAT masquerade let many devices do?", "Apa yang dimungkinkan NAT masquerade bagi banyak perangkat?", ["Share one public IP address||Berbagi satu IP publik", "Get a bigger screen||Mendapat layar lebih besar", "Skip the router||Melewati router"], 0, "Masquerade hides private IPs behind one public IP.", "Masquerade menyembunyikan IP privat di balik satu IP publik."),
  ("Which service gives IP addresses to clients automatically?", "Layanan apa yang memberi IP address ke klien secara otomatis?", ["DHCP", "FTP", "SNMP"], 0, "DHCP leases addresses to clients.", "DHCP meminjamkan alamat IP ke klien.")])

add("Linux administration",
 ("Use the Linux command line to manage files, users and services.", "Memakai command line Linux untuk mengelola file, pengguna, dan layanan."),
 [("Learn the commands ls, cd, pwd, cp, mv and rm and what each does.", "Pelajari perintah ls, cd, pwd, cp, mv, dan rm beserta fungsinya."),
  ("Learn file permissions (rwx) and what chmod 644 means.", "Pelajari izin file (rwx) dan arti chmod 644."),
  ("Learn how to install a package with apt and check a service with systemctl status.", "Pelajari cara memasang paket dengan apt dan memeriksa layanan dengan systemctl status.")],
 ("In a Linux VM: create a folder, a file inside it, change its permission to 640, and show it with ls -l.", "Di VM Linux: buat folder, buat file di dalamnya, ubah izinnya menjadi 640, lalu tampilkan dengan ls -l."),
 [("Which command shows the current directory?", "Perintah apa yang menampilkan folder saat ini?", ["pwd", "cd ..", "mkdir"], 0, "pwd means print working directory.", "pwd berarti print working directory."),
  ("In chmod 644, what can the owner do?", "Pada chmod 644, apa yang boleh dilakukan pemilik file?", ["Read and write||Membaca dan menulis", "Only read||Hanya membaca", "Execute only||Hanya menjalankan"], 0, "6 = read + write, 4 = read only for group and others.", "6 = baca + tulis, 4 = hanya baca untuk grup dan lainnya."),
  ("Which command installs software on Debian or Ubuntu?", "Perintah apa yang memasang software di Debian atau Ubuntu?", ["apt install", "yum remove", "rm -rf"], 0, "apt is the package manager of Debian-based systems.", "apt adalah pengelola paket sistem berbasis Debian.")])

add("Network security",
 ("Know the main threats to a network and the basic ways to defend it.", "Mengetahui ancaman utama jaringan dan cara dasar melindunginya."),
 [("Learn the CIA triad: confidentiality, integrity, availability.", "Pelajari segitiga CIA: kerahasiaan, integritas, ketersediaan."),
  ("Learn what a firewall does and the difference between allow and deny rules.", "Pelajari fungsi firewall dan beda aturan allow dan deny."),
  ("Learn what phishing is and list 3 signs of a phishing message.", "Pelajari apa itu phishing dan tulis 3 ciri pesan phishing.")],
 ("Check your own accounts: turn on two-step verification on one account and write what changed.", "Periksa akunmu sendiri: aktifkan verifikasi dua langkah di satu akun dan tulis apa yang berubah."),
 [("What does a firewall do?", "Apa fungsi firewall?", ["Filters traffic by rules||Menyaring lalu lintas berdasarkan aturan", "Stores files||Menyimpan file", "Speeds up the CPU||Mempercepat CPU"], 0, "A firewall allows or blocks traffic using rules.", "Firewall mengizinkan atau memblokir lalu lintas berdasarkan aturan."),
  ("A fake email asking for your password is called:", "Email palsu yang meminta passwordmu disebut:", ["Phishing", "Routing", "Caching"], 0, "Phishing tricks people into giving secrets.", "Phishing menipu orang agar memberikan data rahasia."),
  ("Which password is strongest?", "Password mana yang paling kuat?", ["12345678", "Kucing2008", "t7!Rk$9mQ2vL"], 2, "Long and random with mixed characters is strongest.", "Panjang, acak, dan campuran karakter paling kuat.")])

add("Troubleshooting",
 ("Find the cause of a problem step by step instead of guessing.", "Mencari penyebab masalah langkah demi langkah, bukan menebak."),
 [("Learn the steps: describe the problem, list possible causes, test one at a time, fix, check.", "Pelajari langkahnya: jelaskan masalah, daftar kemungkinan penyebab, uji satu per satu, perbaiki, cek ulang."),
  ("Learn to check from the bottom up: power, cable, device, settings, software.", "Pelajari pemeriksaan dari bawah ke atas: listrik, kabel, perangkat, pengaturan, software."),
  ("Learn to write down what you changed, so you can undo it.", "Pelajari mencatat apa yang kamu ubah supaya bisa dibatalkan.")],
 ("Take a real problem (for example, slow Wi-Fi at home), list 3 possible causes, and test them one by one.", "Ambil masalah nyata (misalnya Wi-Fi lambat di rumah), daftar 3 kemungkinan penyebab, dan uji satu per satu."),
 [("What should you do first when a computer will not turn on?", "Apa yang sebaiknya dicek pertama saat komputer tidak menyala?", ["Check power and cables||Cek listrik dan kabel", "Reinstall the system||Instal ulang sistem", "Buy a new one||Beli yang baru"], 0, "Start with the simplest, most likely cause.", "Mulai dari penyebab paling sederhana dan paling mungkin."),
  ("Why change only one thing at a time?", "Mengapa mengubah satu hal saja dalam satu waktu?", ["To know which change fixed it||Supaya tahu perubahan mana yang memperbaiki", "To save electricity||Hemat listrik", "It is a rule of the school||Aturan sekolah"], 0, "Many changes at once hide the real cause.", "Banyak perubahan sekaligus menyembunyikan penyebab sebenarnya."),
  ("What is a good last step after a fix?", "Apa langkah terakhir yang baik setelah memperbaiki?", ["Test again and record the result||Uji lagi dan catat hasilnya", "Close the case at once||Langsung selesai", "Turn off the device||Matikan perangkat"], 0, "Confirm the fix works and write it down.", "Pastikan perbaikan berhasil dan catat.")])

add("Python",
 ("Write small Python programs with variables, conditions and loops.", "Menulis program Python kecil dengan variabel, kondisi, dan perulangan."),
 [("Install Python and run print('Hello') in the terminal or an editor.", "Pasang Python dan jalankan print('Hello') di terminal atau editor."),
  ("Learn variables, numbers, strings and lists, and write one example of each.", "Pelajari variabel, angka, string, dan list, lalu tulis satu contoh masing-masing."),
  ("Learn if/else and for loops, and write a loop that prints 1 to 10.", "Pelajari if/else dan for loop, lalu tulis loop yang mencetak 1 sampai 10.")],
 ("Write a program that asks for 3 numbers and prints their average.", "Tulis program yang meminta 3 angka dan mencetak rata-ratanya."),
 [("What does print(2 + 3 * 2) show?", "Apa hasil print(2 + 3 * 2)?", ["8", "10", "12"], 0, "Multiplication comes first: 3*2=6, then 2+6=8.", "Perkalian dulu: 3*2=6, lalu 2+6=8."),
  ("Which keyword starts a loop over a list?", "Kata kunci apa yang memulai perulangan pada sebuah list?", ["for", "def", "import"], 0, "for item in my_list: loops over each item.", "for item in my_list: mengulang tiap item."),
  ("What does len([4, 5, 6]) return?", "Apa hasil len([4, 5, 6])?", ["3", "6", "15"], 0, "len counts items in the list.", "len menghitung jumlah item dalam list.")])

add("SQL",
 ("Read and filter data from a database with SQL.", "Membaca dan menyaring data dari database dengan SQL."),
 [("Learn what a table, row and column are.", "Pelajari apa itu tabel, baris, dan kolom."),
  ("Learn SELECT, FROM and WHERE and write one query with a filter.", "Pelajari SELECT, FROM, dan WHERE lalu tulis satu query dengan filter."),
  ("Learn ORDER BY, COUNT and GROUP BY.", "Pelajari ORDER BY, COUNT, dan GROUP BY.")],
 ("Create a small table of 5 students in SQLite and write 3 queries: all rows, one class only, count per class.", "Buat tabel kecil 5 siswa di SQLite dan tulis 3 query: semua baris, satu kelas saja, jumlah per kelas."),
 [("Which clause filters rows?", "Klausa apa yang menyaring baris?", ["WHERE", "ORDER BY", "FROM"], 0, "WHERE keeps only rows that match.", "WHERE hanya menyisakan baris yang cocok."),
  ("SELECT COUNT(*) FROM students returns:", "SELECT COUNT(*) FROM students menghasilkan:", ["The number of rows||Jumlah baris", "All names||Semua nama", "The first row||Baris pertama"], 0, "COUNT(*) counts rows.", "COUNT(*) menghitung baris."),
  ("Which sorts results from highest to lowest?", "Mana yang mengurutkan hasil dari terbesar ke terkecil?", ["ORDER BY score DESC", "SORT score UP", "GROUP score"], 0, "DESC means descending.", "DESC berarti menurun.")])

add("Excel",
 ("Use formulas and simple tables to organise and sum numbers.", "Memakai rumus dan tabel sederhana untuk menata dan menjumlah angka."),
 [("Learn cells, rows, columns and how to write a formula that starts with =.", "Pelajari sel, baris, kolom, dan cara menulis rumus yang diawali =."),
  ("Learn SUM, AVERAGE, IF and VLOOKUP (or XLOOKUP).", "Pelajari SUM, AVERAGE, IF, dan VLOOKUP (atau XLOOKUP)."),
  ("Learn how to sort, filter and make a simple chart.", "Pelajari cara mengurutkan, menyaring, dan membuat grafik sederhana.")],
 ("Make a monthly allowance sheet with income, expenses, a SUM total and a chart.", "Buat lembar uang saku bulanan dengan pemasukan, pengeluaran, total SUM, dan grafik."),
 [("Which formula adds A1 to A10?", "Rumus mana yang menjumlahkan A1 sampai A10?", ["=SUM(A1:A10)", "=ADD(A1,A10)", "=A1+A10+"], 0, "SUM adds a range.", "SUM menjumlahkan sebuah rentang."),
  ("What does =IF(B2>=75,\"Pass\",\"Fail\") do?", "Apa fungsi =IF(B2>=75,\"Pass\",\"Fail\")?", ["Shows Pass if B2 is 75 or more||Menampilkan Pass jika B2 sama dengan atau lebih dari 75", "Adds 75 to B2||Menambah 75 ke B2", "Deletes B2||Menghapus B2"], 0, "IF tests a condition and returns one of two results.", "IF menguji kondisi dan memberi salah satu dari dua hasil."),
  ("Which formula finds the average of B2:B6?", "Rumus mana yang mencari rata-rata B2:B6?", ["=AVERAGE(B2:B6)", "=MEAN(B2-B6)", "=AVG B2"], 0, "AVERAGE returns the mean.", "AVERAGE memberi nilai rata-rata.")])

add("Data analysis",
 ("Turn a table of numbers into a clear finding.", "Mengubah tabel angka menjadi temuan yang jelas."),
 [("Learn the steps: question, collect, clean, analyse, show.", "Pelajari langkahnya: pertanyaan, kumpulkan, bersihkan, analisis, tampilkan."),
  ("Learn mean, median, minimum and maximum and when the median is better than the mean.", "Pelajari rata-rata, median, minimum, dan maksimum serta kapan median lebih baik daripada rata-rata."),
  ("Learn to pick a chart: bar for categories, line for time.", "Pelajari memilih grafik: batang untuk kategori, garis untuk waktu.")],
 ("Collect the daily screen time of 10 classmates, find the mean and median, and draw one chart.", "Kumpulkan waktu layar harian 10 teman, cari rata-rata dan median, lalu gambar satu grafik."),
 [("Which chart is best to show change over months?", "Grafik apa yang cocok untuk perubahan antar bulan?", ["Line chart||Grafik garis", "Pie chart||Diagram lingkaran", "Table only||Tabel saja"], 0, "Lines show trends over time.", "Garis menunjukkan tren dari waktu ke waktu."),
  ("The median of 2, 3, 100 is:", "Median dari 2, 3, 100 adalah:", ["3", "35", "100"], 0, "The median is the middle value after sorting.", "Median adalah nilai tengah setelah diurutkan."),
  ("What is data cleaning?", "Apa itu pembersihan data?", ["Fixing or removing wrong and missing values||Memperbaiki atau membuang data salah dan kosong", "Deleting the whole file||Menghapus seluruh file", "Making the chart colourful||Membuat grafik berwarna"], 0, "Bad data gives bad conclusions.", "Data buruk menghasilkan kesimpulan buruk.")])

add("HTML/CSS",
 ("Build a simple web page and style it.", "Membuat halaman web sederhana dan menatanya."),
 [("Learn the structure of a page: html, head, body and common tags (h1, p, a, img, ul).", "Pelajari struktur halaman: html, head, body dan tag umum (h1, p, a, img, ul)."),
  ("Learn how CSS selects elements and sets color, font and spacing.", "Pelajari cara CSS memilih elemen dan mengatur warna, huruf, dan jarak."),
  ("Learn flexbox to put items in a row or column.", "Pelajari flexbox untuk menata item dalam baris atau kolom.")],
 ("Make a one-page profile of yourself with a heading, photo, list of skills and a link, styled with at least 5 CSS rules.", "Buat satu halaman profil dirimu dengan judul, foto, daftar skill, dan tautan, ditata dengan minimal 5 aturan CSS."),
 [("Which tag makes a link?", "Tag apa yang membuat tautan?", ["<a>", "<p>", "<img>"], 0, "The a (anchor) tag with href makes a link.", "Tag a (anchor) dengan href membuat tautan."),
  ("In CSS, what does color: red; change?", "Di CSS, apa yang diubah color: red;?", ["Text color||Warna teks", "Page width||Lebar halaman", "Font size||Ukuran huruf"], 0, "color sets the text color.", "color mengatur warna teks."),
  ("Which CSS makes children sit in a row?", "CSS mana yang menata anak elemen dalam satu baris?", ["display: flex;", "display: none;", "position: off;"], 0, "Flexbox lays items out in a row by default.", "Flexbox menata item dalam baris secara bawaan.")])

add("JavaScript",
 ("Make a web page react to clicks with JavaScript.", "Membuat halaman web bereaksi terhadap klik dengan JavaScript."),
 [("Learn let, const, numbers, strings, arrays and functions.", "Pelajari let, const, angka, string, array, dan fungsi."),
  ("Learn document.querySelector and addEventListener('click', ...).", "Pelajari document.querySelector dan addEventListener('click', ...)."),
  ("Open the browser console (F12) and test small code lines.", "Buka console browser (F12) dan coba baris kode kecil.")],
 ("Make a button that adds 1 to a counter shown on the page.", "Buat tombol yang menambah 1 pada penghitung yang tampil di halaman."),
 [("Which keyword makes a value that cannot be reassigned?", "Kata kunci apa yang membuat nilai tidak bisa diisi ulang?", ["const", "let", "var only||hanya var"], 0, "const creates a constant binding.", "const membuat ikatan konstan."),
  ("What does addEventListener('click', f) do?", "Apa fungsi addEventListener('click', f)?", ["Runs f when the element is clicked||Menjalankan f saat elemen diklik", "Deletes the element||Menghapus elemen", "Reloads the page||Memuat ulang halaman"], 0, "It registers a function for the click event.", "Ia mendaftarkan fungsi untuk peristiwa klik."),
  ("What is 5 + '5' in JavaScript?", "Berapa 5 + '5' di JavaScript?", ["'55'", "10", "Error"], 0, "A number plus a string joins them as text.", "Angka ditambah string digabung sebagai teks.")])

add("Git",
 ("Save versions of your work and share it with Git and GitHub.", "Menyimpan versi pekerjaanmu dan membagikannya dengan Git dan GitHub."),
 [("Install Git and run git --version.", "Pasang Git dan jalankan git --version."),
  ("Learn git init, git add, git commit and git status.", "Pelajari git init, git add, git commit, dan git status."),
  ("Create a GitHub account and learn git push.", "Buat akun GitHub dan pelajari git push.")],
 ("Create a repo for a small project, make 3 commits with clear messages, and push it to GitHub.", "Buat repo untuk proyek kecil, buat 3 commit dengan pesan jelas, lalu push ke GitHub."),
 [("Which command saves a snapshot of staged changes?", "Perintah apa yang menyimpan snapshot perubahan yang sudah di-stage?", ["git commit", "git clone", "git pull"], 0, "commit records the snapshot.", "commit mencatat snapshot."),
  ("What does git add . do?", "Apa fungsi git add .?", ["Stages all changes||Men-stage semua perubahan", "Deletes the repo||Menghapus repo", "Uploads to GitHub||Mengunggah ke GitHub"], 0, "add prepares changes for commit.", "add menyiapkan perubahan untuk di-commit."),
  ("Which command sends commits to GitHub?", "Perintah apa yang mengirim commit ke GitHub?", ["git push", "git init", "git status"], 0, "push uploads commits to the remote.", "push mengunggah commit ke remote.")])

add("Machine learning",
 ("Understand how a model learns from data, and train a very small one.", "Memahami bagaimana model belajar dari data, dan melatih model yang sangat kecil."),
 [("Learn the idea: data in, model learns a pattern, then predicts new cases.", "Pelajari idenya: data masuk, model mempelajari pola, lalu memprediksi kasus baru."),
  ("Learn training data versus test data, and why we keep some data hidden.", "Pelajari data latih dan data uji, dan mengapa sebagian data disembunyikan."),
  ("Learn overfitting: a model that memorises instead of learning.", "Pelajari overfitting: model yang menghafal, bukan belajar.")],
 ("With Python and scikit-learn (or a no-code tool), train a model on a small dataset and report its accuracy on test data.", "Dengan Python dan scikit-learn (atau alat tanpa kode), latih model pada dataset kecil dan laporkan akurasinya pada data uji."),
 [("Why do we test on data the model has not seen?", "Mengapa kita menguji pada data yang belum pernah dilihat model?", ["To check it can generalise||Untuk memeriksa kemampuannya menggeneralisasi", "To make training faster||Agar pelatihan lebih cepat", "To hide errors||Untuk menyembunyikan kesalahan"], 0, "Test data shows real performance.", "Data uji menunjukkan kinerja sebenarnya."),
  ("A model that is perfect on training data but poor on new data is:", "Model yang sempurna pada data latih tetapi buruk pada data baru disebut:", ["Overfitted||Overfitting", "Underpaid||Underpaid", "Compiled||Terkompilasi"], 0, "That is overfitting.", "Itu overfitting."),
  ("Predicting a house price is a task of:", "Memprediksi harga rumah adalah tugas:", ["Regression||Regresi", "Classification||Klasifikasi", "Encryption||Enkripsi"], 0, "Predicting a number is regression.", "Memprediksi angka adalah regresi.")])

add("Accounting basics",
 ("Understand assets, liabilities and equity and record simple transactions.", "Memahami aset, kewajiban, dan modal serta mencatat transaksi sederhana."),
 [("Learn the equation: Assets = Liabilities + Equity.", "Pelajari persamaan: Aset = Kewajiban + Modal."),
  ("Learn debit and credit and which side increases an asset.", "Pelajari debit dan kredit dan sisi mana yang menambah aset."),
  ("Learn the accounting cycle in short: transaction, journal, ledger, trial balance, statements.", "Pelajari siklus akuntansi singkat: transaksi, jurnal, buku besar, neraca saldo, laporan.")],
 ("Record 5 transactions of a small shop in a journal (date, account, debit, credit).", "Catat 5 transaksi sebuah warung kecil dalam jurnal (tanggal, akun, debit, kredit)."),
 [("Which is an asset?", "Mana yang termasuk aset?", ["Cash||Kas", "Bank loan||Utang bank", "Owner's capital||Modal pemilik"], 0, "Cash is something the business owns.", "Kas adalah sesuatu yang dimiliki usaha."),
  ("Assets = ?", "Aset = ?", ["Liabilities + Equity||Kewajiban + Modal", "Revenue - Expense||Pendapatan - Beban", "Debit - Credit||Debit - Kredit"], 0, "This is the basic accounting equation.", "Ini persamaan dasar akuntansi."),
  ("Buying equipment with cash: what is debited?", "Membeli peralatan dengan kas: apa yang didebit?", ["Equipment||Peralatan", "Cash||Kas", "Capital||Modal"], 0, "Equipment (an asset) increases, so it is debited; cash is credited.", "Peralatan (aset) bertambah sehingga didebit; kas dikredit.")])

add("Bookkeeping",
 ("Keep clean records of money in and money out.", "Menjaga catatan rapi tentang uang masuk dan uang keluar."),
 [("Learn the cash book and the difference between receipts and payments.", "Pelajari buku kas dan beda penerimaan dan pengeluaran."),
  ("Learn why every entry needs proof such as an invoice or receipt.", "Pelajari mengapa setiap catatan butuh bukti seperti faktur atau kuitansi."),
  ("Learn how to do a bank or cash reconciliation.", "Pelajari cara melakukan rekonsiliasi bank atau kas.")],
 ("Keep a cash book for one week of your own spending and check that your balance matches your real cash.", "Buat buku kas untuk pengeluaranmu selama satu minggu dan cek apakah saldonya cocok dengan uang sebenarnya."),
 [("Why keep receipts?", "Mengapa menyimpan kuitansi?", ["They prove a transaction happened||Sebagai bukti transaksi terjadi", "They decorate the book||Menghias buku", "They are optional always||Selalu opsional"], 0, "Records need evidence.", "Catatan butuh bukti."),
  ("Opening cash 100,000; received 50,000; paid 30,000. Closing cash?", "Kas awal 100.000; terima 50.000; bayar 30.000. Kas akhir?", ["120,000", "180,000", "80,000"], 0, "100,000 + 50,000 - 30,000 = 120,000.", "100.000 + 50.000 - 30.000 = 120.000."),
  ("A mismatch between book and real cash is found by:", "Selisih antara buku dan kas sebenarnya ditemukan dengan:", ["Reconciliation||Rekonsiliasi", "Printing||Mencetak", "Rounding||Membulatkan"], 0, "Reconciliation compares the two.", "Rekonsiliasi membandingkan keduanya.")])

add("Tax regulations",
 ("Know the basic kinds of tax in Indonesia and who must pay them.", "Mengetahui jenis pajak dasar di Indonesia dan siapa yang wajib membayarnya."),
 [("Learn the difference between PPh (income tax) and PPN (value added tax).", "Pelajari beda PPh (pajak penghasilan) dan PPN (pajak pertambahan nilai)."),
  ("Learn what an NPWP is and what SPT means.", "Pelajari apa itu NPWP dan arti SPT."),
  ("Check the current rates and rules on the official site of the tax office (pajak.go.id), because rules change.", "Cek tarif dan aturan terbaru di situs resmi kantor pajak (pajak.go.id), karena aturan bisa berubah.")],
 ("Write a one-page summary of the tax types a small shop pays and find where the rates are published.", "Tulis ringkasan satu halaman tentang jenis pajak yang dibayar warung kecil dan cari di mana tarifnya diumumkan."),
 [("PPN is a tax on:", "PPN adalah pajak atas:", ["Goods and services consumed||Barang dan jasa yang dikonsumsi", "Salary only||Gaji saja", "Land only||Tanah saja"], 0, "PPN is value added tax on consumption.", "PPN adalah pajak pertambahan nilai atas konsumsi."),
  ("SPT stands for:", "SPT adalah singkatan dari:", ["Surat Pemberitahuan (tax return)||Surat Pemberitahuan (laporan pajak)", "Sistem Pajak Tunai||Sistem Pajak Tunai", "Surat Pajak Tetap||Surat Pajak Tetap"], 0, "SPT is the tax return.", "SPT adalah laporan pajak."),
  ("Where should you check current tax rates?", "Di mana sebaiknya mengecek tarif pajak terbaru?", ["The official tax office site||Situs resmi kantor pajak", "A friend's chat||Chat teman", "An old textbook||Buku lama"], 0, "Rules change, so use the official source.", "Aturan berubah, jadi pakai sumber resmi.")])

add("Financial reporting",
 ("Read and prepare a simple income statement and balance sheet.", "Membaca dan menyusun laporan laba rugi dan neraca sederhana."),
 [("Learn what the income statement shows: revenue minus expenses equals profit.", "Pelajari isi laporan laba rugi: pendapatan dikurangi beban sama dengan laba."),
  ("Learn what the balance sheet shows at one date.", "Pelajari isi neraca pada satu tanggal."),
  ("Learn why a report must be accurate, on time and consistent.", "Pelajari mengapa laporan harus akurat, tepat waktu, dan konsisten.")],
 ("Make an income statement for a small business for one month with made-up numbers.", "Buat laporan laba rugi untuk usaha kecil selama satu bulan dengan angka rekaan."),
 [("Revenue 5,000,000 and expenses 3,500,000. Profit?", "Pendapatan 5.000.000 dan beban 3.500.000. Laba?", ["1,500,000", "8,500,000", "3,500,000"], 0, "Profit = revenue - expenses.", "Laba = pendapatan - beban."),
  ("A balance sheet shows the position:", "Neraca menunjukkan posisi:", ["At one date||Pada satu tanggal", "Over a whole year||Selama satu tahun penuh", "Of only profit||Hanya laba"], 0, "It is a snapshot.", "Ia seperti foto sesaat."),
  ("Which statement shows profit?", "Laporan mana yang menunjukkan laba?", ["Income statement||Laba rugi", "Balance sheet||Neraca", "Cash book||Buku kas"], 0, "The income statement shows profit or loss.", "Laba rugi menunjukkan laba atau rugi.")])

add("Accounting software",
 ("Record transactions in accounting software instead of on paper.", "Mencatat transaksi di software akuntansi, bukan di kertas."),
 [("Pick a free or trial accounting program your teacher recommends and install it.", "Pilih program akuntansi gratis atau uji coba yang disarankan gurumu dan pasang."),
  ("Learn how to create a chart of accounts and enter an opening balance.", "Pelajari cara membuat daftar akun dan memasukkan saldo awal."),
  ("Learn how to enter an invoice and print a report.", "Pelajari cara memasukkan faktur dan mencetak laporan.")],
 ("Enter 5 sample transactions and print a trial balance.", "Masukkan 5 transaksi contoh dan cetak neraca saldo."),
 [("What is a chart of accounts?", "Apa itu daftar akun (chart of accounts)?", ["A list of all accounts used||Daftar semua akun yang dipakai", "A bar chart||Grafik batang", "A bank statement||Rekening koran"], 0, "It organises every account.", "Ia menata semua akun."),
  ("Why enter opening balances?", "Mengapa memasukkan saldo awal?", ["So reports start from correct amounts||Agar laporan dimulai dari jumlah yang benar", "To slow the program||Memperlambat program", "No reason||Tidak ada alasan"], 0, "Reports depend on correct starting amounts.", "Laporan bergantung pada saldo awal yang benar."),
  ("A trial balance checks that:", "Neraca saldo memeriksa bahwa:", ["Total debits equal total credits||Total debit sama dengan total kredit", "Profit is high||Laba tinggi", "All receipts are printed||Semua kuitansi dicetak"], 0, "Debits must equal credits.", "Debit harus sama dengan kredit.")])

add("Communication",
 ("Say and write things so that others understand you the first time.", "Berbicara dan menulis agar orang lain paham pada kali pertama."),
 [("Learn to start with the main point, then give 2 or 3 reasons.", "Belajar memulai dengan inti, lalu beri 2 atau 3 alasan."),
  ("Learn active listening: repeat in your own words what you heard.", "Belajar mendengarkan aktif: ulangi dengan kata-katamu apa yang kamu dengar."),
  ("Learn to write a polite, short message to a teacher or a company.", "Belajar menulis pesan singkat yang sopan kepada guru atau perusahaan.")],
 ("Write a 5-line message asking a company for an internship, then ask a friend if it is clear.", "Tulis pesan 5 baris untuk meminta magang ke sebuah perusahaan, lalu tanya temanmu apakah sudah jelas."),
 [("What is active listening?", "Apa itu mendengarkan aktif?", ["Checking you understood by repeating it back||Memastikan paham dengan mengulang kembali", "Waiting to talk||Menunggu giliran bicara", "Looking at your phone||Melihat ponsel"], 0, "Repeating back confirms understanding.", "Mengulang kembali memastikan pemahaman."),
  ("A good message starts with:", "Pesan yang baik dimulai dengan:", ["The main point||Inti pesan", "A long story||Cerita panjang", "An apology||Permintaan maaf"], 0, "Lead with the point.", "Mulai dari inti."),
  ("Which greeting suits a first email to a company?", "Sapaan mana yang cocok untuk email pertama ke perusahaan?", ["Dear Sir/Madam||Yth. Bapak/Ibu", "Hey bro||Halo bro", "Yo||Woy"], 0, "Be polite and formal at first.", "Bersikap sopan dan formal di awal.")])

add("Teamwork",
 ("Work with others so the whole result is better than the parts.", "Bekerja bersama orang lain agar hasil bersama lebih baik daripada sendiri-sendiri."),
 [("Learn to share roles: who does what, by when.", "Belajar membagi peran: siapa mengerjakan apa, kapan selesai."),
  ("Learn how to give feedback on the work, not on the person.", "Belajar memberi masukan pada pekerjaan, bukan pada orangnya."),
  ("Learn what to do when a teammate is late: ask first, then help.", "Belajar apa yang dilakukan jika teman terlambat: tanya dulu, lalu bantu.")],
 ("In your next group task write down the roles and deadlines before starting, and check them after.", "Pada tugas kelompok berikutnya tulis peran dan tenggat sebelum mulai, lalu cek setelahnya."),
 [("Good feedback focuses on:", "Masukan yang baik berfokus pada:", ["The work||Pekerjaannya", "The person||Orangnya", "The mood||Suasana hati"], 0, "Talk about the work, not the person.", "Bicarakan pekerjaannya, bukan orangnya."),
  ("Why set roles in a group?", "Mengapa membagi peran dalam kelompok?", ["So everyone knows their part||Agar semua tahu bagiannya", "So one person does everything||Agar satu orang mengerjakan semuanya", "To avoid meeting||Agar tidak perlu rapat"], 0, "Clear roles prevent gaps and overlap.", "Peran jelas mencegah celah dan tumpang tindih."),
  ("A teammate is late. First you should:", "Teman terlambat. Pertama-tama kamu:", ["Ask what is blocking them||Tanya apa kendalanya", "Complain to others||Mengeluh ke orang lain", "Ignore it||Mengabaikan"], 0, "Understand the cause, then help.", "Pahami penyebabnya, lalu bantu.")])

add("Problem solving",
 ("Break a problem into parts and test ideas.", "Memecah masalah menjadi bagian-bagian dan menguji ide."),
 [("Learn to restate the problem in one sentence.", "Belajar menyatakan ulang masalah dalam satu kalimat."),
  ("Learn to break a big problem into 3 to 5 small ones.", "Belajar memecah masalah besar menjadi 3 sampai 5 masalah kecil."),
  ("Learn to try the simplest idea first and learn from failed tries.", "Belajar mencoba ide paling sederhana dulu dan belajar dari percobaan yang gagal.")],
 ("Pick a real problem at school (for example long queues in the canteen) and write 3 ideas and how you would test each.", "Pilih masalah nyata di sekolah (misalnya antrean panjang di kantin) dan tulis 3 ide beserta cara mengujinya."),
 [("The first step in solving a problem is:", "Langkah pertama menyelesaikan masalah adalah:", ["Understand it clearly||Memahaminya dengan jelas", "Pick a tool||Memilih alat", "Ask for the answer||Meminta jawaban"], 0, "Know the problem before solving it.", "Pahami masalah sebelum menyelesaikannya."),
  ("Why split a big problem?", "Mengapa memecah masalah besar?", ["Small parts are easier to solve||Bagian kecil lebih mudah diselesaikan", "To make it longer||Agar lebih lama", "No reason||Tanpa alasan"], 0, "Divide and conquer.", "Pecah lalu selesaikan."),
  ("A failed idea is:", "Ide yang gagal adalah:", ["Information for the next try||Informasi untuk percobaan berikutnya", "A waste||Sia-sia", "Proof you cannot||Bukti kamu tidak mampu"], 0, "Failures teach what does not work.", "Kegagalan mengajarkan apa yang tidak berhasil.")])

add("Attention to detail",
 ("Catch small mistakes before they become big ones.", "Menangkap kesalahan kecil sebelum menjadi besar."),
 [("Learn to re-read your work after a short break.", "Belajar membaca ulang pekerjaanmu setelah istirahat sebentar."),
  ("Learn to use a checklist for repeated tasks.", "Belajar memakai daftar periksa untuk tugas yang berulang."),
  ("Learn to double-check numbers, names and dates.", "Belajar memeriksa ulang angka, nama, dan tanggal.")],
 ("Take one of your reports, make a 5-item checklist, and use it to find at least 2 corrections.", "Ambil salah satu laporanmu, buat daftar periksa 5 butir, dan pakai untuk menemukan minimal 2 koreksi."),
 [("Which helps most to find mistakes?", "Mana yang paling membantu menemukan kesalahan?", ["A checklist||Daftar periksa", "Working faster||Bekerja lebih cepat", "Skipping review||Melewatkan pemeriksaan"], 0, "A checklist makes checking systematic.", "Daftar periksa membuat pemeriksaan sistematis."),
  ("Why re-read after a break?", "Mengapa membaca ulang setelah istirahat?", ["Fresh eyes see more errors||Mata yang segar melihat lebih banyak kesalahan", "To waste time||Membuang waktu", "To sleep||Untuk tidur"], 0, "A break helps you see errors.", "Istirahat membantu melihat kesalahan."),
  ("Which should always be double-checked in an invoice?", "Mana yang harus selalu diperiksa ulang pada faktur?", ["Amounts and names||Jumlah dan nama", "Font style||Gaya huruf", "Paper colour||Warna kertas"], 0, "Money and identities must be right.", "Uang dan identitas harus benar.")])

add("Customer service",
 ("Help a customer politely and solve their problem.", "Membantu pelanggan dengan sopan dan menyelesaikan masalahnya."),
 [("Learn to greet, listen to the whole problem, and not interrupt.", "Belajar menyapa, mendengar seluruh masalah, dan tidak memotong."),
  ("Learn to say what you can do, not only what you cannot.", "Belajar menyampaikan apa yang bisa dilakukan, bukan hanya yang tidak bisa."),
  ("Learn to follow up after the problem is solved.", "Belajar menindaklanjuti setelah masalah selesai.")],
 ("Role-play with a friend: one is an upset customer, one helps. Swap roles and note what worked.", "Bermain peran dengan teman: satu menjadi pelanggan kesal, satu membantu. Tukar peran dan catat apa yang berhasil."),
 [("An angry customer is talking. You should first:", "Pelanggan marah sedang berbicara. Pertama-tama kamu:", ["Listen fully||Mendengarkan sampai selesai", "Argue back||Membantah", "Walk away||Pergi"], 0, "Listening calms and gives you facts.", "Mendengar menenangkan dan memberi fakta."),
  ("If you cannot do what they ask, you should:", "Jika tidak bisa melakukan permintaannya, kamu sebaiknya:", ["Offer what you can do||Menawarkan apa yang bisa dilakukan", "Say no and stop||Bilang tidak lalu berhenti", "Promise anything||Berjanji apa saja"], 0, "Offer an alternative honestly.", "Tawarkan alternatif dengan jujur."),
  ("Why follow up?", "Mengapa menindaklanjuti?", ["To check they are satisfied||Untuk memastikan mereka puas", "To sell more only||Hanya untuk menjual lebih", "It is not needed||Tidak perlu"], 0, "Follow-up builds trust.", "Tindak lanjut membangun kepercayaan.")])

PASS = 0.7

def generic(lang):
    """Panduan untuk skill yang belum punya materi tertulis (karier tambahan): langkah umum + daftar periksa 'bisa melakukan'."""
    if lang == "id":
        return {"goal": "Memahami dasar skill ini dan menunjukkannya lewat contoh kecil.",
                "steps": ["Cari satu materi pemula (buku, video, atau guru) tentang {s} dan tulis 5 poin penting.", "Cari satu contoh nyata {s} di dunia kerja dan tulis apa yang dikerjakan orangnya.", "Tulis 3 hal yang masih belum kamu mengerti dan tanyakan ke gurumu."],
                "practice": "Buat satu contoh kecil yang memakai {s}, lalu jelaskan hasilnya dengan kata-katamu sendiri."}
    return {"goal": "Understand the basics of this skill and show it with a small example.",
            "steps": ["Find one beginner source (book, video or teacher) about {s} and write down 5 key points.", "Find one real example of {s} at work and write what the person does.", "Write 3 things you still do not understand and ask your teacher."],
            "practice": "Make one small example that uses {s}, then explain the result in your own words."}
