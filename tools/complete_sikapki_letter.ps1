$ErrorActionPreference = 'Stop'
$source = 'C:\Users\Dfive\Downloads\DRAFT SURAT PUSDATIN_dic (1).docx'
$output = Join-Path (Get-Location) 'DRAFT SURAT PUSDATIN_SIKAP-KI_LENGKAP.docx'

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open($source)
$doc.SaveAs2($output)

$sel = $word.Selection
$sel.EndKey(6) # wdStory
$sel.InsertBreak(7) # wdPageBreak

function Add-Heading([string]$text, [int]$level = 1) {
    $sel.Style = "Heading $level"
    $sel.TypeText($text)
    $sel.TypeParagraph()
    $sel.Style = 'Normal'
}

function Add-Para([string]$text) {
    $sel.Style = 'Normal'
    $sel.TypeText($text)
    $sel.TypeParagraph()
}

Add-Heading 'LAMPIRAN TAMBAHAN: FLOWCHART DAN PROSES BISNIS SIKAP-KI NTB' 1
Add-Para 'Lampiran ini menjelaskan alur layanan dan proses bisnis SIKAP-KI NTB sebagai bahan penelaahan dan verifikasi teknis. SIKAP-KI merupakan kanal informasi dan konsultasi awal; keputusan hukum dan pemeriksaan resmi tetap menjadi kewenangan DJKI.'

Add-Heading 'A. Flowchart Umum Layanan' 2
Add-Para 'MULAI -> Pengguna membuka SIKAP-KI -> Memilih layanan (Chatbot / Cek Kelas Merek / FAQ / Checklist) -> Mengisi pertanyaan atau data -> Sistem memvalidasi input -> Sistem memproses menggunakan basis pengetahuan dan/atau AI -> Hasil awal ditampilkan beserta sumber dan batasan -> [Perlu pendalaman?] Jika TIDAK: SELESAI; jika YA: konsultasi diteruskan ke petugas -> Petugas memberikan arahan -> Status konsultasi diperbarui -> SELESAI.'

Add-Heading 'B. Flowchart Chatbot Helpdesk KI' 2
Add-Para 'MULAI -> Pengguna mengetik pertanyaan -> Sistem memeriksa konteks pertanyaan -> Pertanyaan diubah menjadi pencarian semantik -> Sistem mencari dokumen/FAQ resmi yang relevan -> [Konteks cukup?] Jika YA: AI menyusun jawaban berdasarkan sumber -> Jawaban dan sumber ditampilkan -> Pengguna dapat memberi rating -> SELESAI. Jika TIDAK: sistem menampilkan arahan bahwa pertanyaan memerlukan petugas -> membuat ID pelacakan -> petugas menerima dan menindaklanjuti -> status konsultasi diperbarui -> SELESAI.'

Add-Heading 'C. Flowchart Asisten Penelusuran Kelas Merek' 2
Add-Para 'MULAI -> Pengguna memasukkan nama merek dan uraian barang/jasa -> Sistem memvalidasi kelengkapan data -> Sistem mencocokkan uraian dengan istilah Nice Classification -> AI menyusun maksimal tiga rekomendasi kelas beserta alasan -> [Uraian ambigu?] Jika YA: sistem meminta klarifikasi -> pengguna melengkapi uraian -> proses pencocokan diulang. Jika TIDAK: hasil rekomendasi, disclaimer, dan tautan PDKI/SKM ditampilkan -> aktivitas dicatat sebagai log anonim -> SELESAI.'

Add-Heading 'D. Flowchart Pengelolaan Basis Pengetahuan' 2
Add-Para 'Petugas mengunggah dokumen/FAQ -> Admin memeriksa sumber dan isi -> [Valid?] Jika TIDAK: dikembalikan untuk perbaikan. Jika YA: status menjadi terverifikasi -> dokumen dipecah menjadi potongan teks -> sistem membuat embedding -> indeks pencarian diperbarui -> sumber aktif digunakan chatbot -> perubahan dapat dipantau melalui Admin -> SELESAI.'

Add-Heading 'E. Proses Bisnis Utama' 2
$table = $doc.Tables.Add($sel.Range, 1, 5)
$table.Style = 'Table Grid'
$headers = @('No.', 'Aktor', 'Input', 'Proses', 'Output')
for ($i = 1; $i -le 5; $i++) { $table.Cell(1,$i).Range.Text = $headers[$i-1] }
$rows = @(
    @('1','Masyarakat','Pertanyaan atau kebutuhan KI','Mengakses layanan dan mengirimkan pertanyaan melalui website','Permintaan layanan tercatat'),
    @('2','Sistem SIKAP-KI','Pertanyaan pengguna','Validasi, klasifikasi konteks, pencarian sumber, dan pemrosesan AI','Jawaban awal beserta sumber'),
    @('3','Masyarakat','Uraian barang/jasa merek','Mengisi data dan menerima rekomendasi kelas Nice','Rekomendasi kelas dan langkah verifikasi'),
    @('4','Sistem SIKAP-KI','Jawaban atau hasil analisis','Menampilkan disclaimer, menyimpan log, dan menyediakan rating','Riwayat layanan dan data monitoring'),
    @('5','Petugas Helpdesk KI','Konsultasi yang dieskalasi','Menelaah pertanyaan, memberi arahan, dan memperbarui status','Jawaban/tindak lanjut petugas'),
    @('6','Admin/Pengelola KI','Dokumen, FAQ, atau regulasi baru','Memvalidasi, memperbarui, dan mengindeks basis pengetahuan','Sumber pengetahuan yang mutakhir')
)
foreach ($row in $rows) {
    $cells = $table.Rows.Add().Cells
    for ($i = 1; $i -le 5; $i++) { $cells.Item($i).Range.Text = $row[$i-1] }
}
$sel.EndKey(6)
$sel.TypeParagraph()

Add-Heading 'F. Aturan Pengendalian dan Batasan' 2
$controlText = "1) Jawaban AI bersifat informatif dan berbasis sumber yang telah diverifikasi. 2) Pertanyaan yang tidak memiliki konteks cukup atau memerlukan penilaian substantif dialihkan kepada petugas. 3) Rekomendasi kelas merek bukan keputusan penerimaan merek. 4) Data administratif, log, dan basis pengetahuan dikelola oleh pengguna berwenang. 5) PDKI, SKM DJKI, dan sistem permohonan resmi tetap menjadi rujukan final."
Add-Para $controlText

$doc.Save()
$doc.Close()
$word.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($sel) | Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) | Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
Write-Output $output
