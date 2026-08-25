from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
from xml.sax.saxutils import escape

source = Path(r'C:\Users\Dfive\Downloads\DRAFT SURAT PUSDATIN_dic (1).docx')
output = Path('DRAFT SURAT PUSDATIN_SIKAP-KI_LENGKAP.docx')

def para(text, bold=False, size='20'):
    rpr = f'<w:b/><w:sz w:val="{size}"/>' if bold else f'<w:sz w:val="{size}"/>'
    return f'<w:p><w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

def row(cells):
    return '<w:tr>' + ''.join(f'<w:tc><w:p><w:r><w:t>{escape(c)}</w:t></w:r></w:p></w:tc>' for c in cells) + '</w:tr>'

extra = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
extra += para('LAMPIRAN TAMBAHAN: FLOWCHART DAN PROSES BISNIS SIKAP-KI NTB', True, '28')
extra += para('Lampiran ini menjadi bahan penelaahan dan verifikasi teknis. SIKAP-KI adalah kanal informasi dan konsultasi awal; keputusan hukum dan pemeriksaan resmi tetap menjadi kewenangan DJKI.')
for title, text in [
    ('1. Flowchart Umum Layanan', 'MULAI -> Pengguna membuka website -> Memilih layanan -> Mengisi pertanyaan/data -> Sistem memvalidasi input -> Sistem memproses basis pengetahuan dan/atau AI -> Hasil awal ditampilkan beserta sumber -> [Perlu pendalaman?] TIDAK: SELESAI; YA: diteruskan ke petugas -> Petugas memberi arahan -> Status diperbarui -> SELESAI.'),
    ('2. Flowchart Chatbot Helpdesk KI', 'MULAI -> Pengguna mengetik pertanyaan -> Sistem memeriksa konteks -> Mencari dokumen/FAQ resmi -> [Konteks cukup?] YA: AI menyusun jawaban berbasis sumber -> Jawaban ditampilkan -> Rating -> SELESAI. TIDAK: membuat ID pelacakan -> petugas menindaklanjuti -> status diperbarui -> SELESAI.'),
    ('3. Flowchart Asisten Penelusuran Kelas Merek', 'MULAI -> Pengguna memasukkan nama merek dan uraian barang/jasa -> Validasi data -> Pencocokan Nice Classification -> AI menyusun maksimal tiga rekomendasi -> [Uraian ambigu?] YA: minta klarifikasi dan ulangi. TIDAK: tampilkan hasil, disclaimer, dan tautan PDKI/SKM -> simpan log anonim -> SELESAI.'),
    ('4. Flowchart Pengelolaan Basis Pengetahuan', 'Petugas mengunggah dokumen/FAQ -> Admin memeriksa -> [Valid?] TIDAK: perbaikan. YA: status terverifikasi -> teks dipecah -> embedding dibuat -> indeks diperbarui -> sumber aktif digunakan chatbot -> SELESAI.'),
]:
    extra += para(title, True, '22') + para(text)
extra += para('5. Proses Bisnis Utama', True, '22')
table = '<w:tbl><w:tblPr><w:tblBorders>' + ''.join(f'<w:{x} w:val="single" w:sz="4" w:space="0" w:color="808080"/>' for x in ('top','left','bottom','right','insideH','insideV')) + '</w:tblBorders></w:tblPr>'
table += row(['No.','Aktor','Input','Proses','Output'])
for r in [
    ['1','Masyarakat','Pertanyaan/kebutuhan KI','Mengakses layanan dan mengirim pertanyaan','Permintaan tercatat'],
    ['2','Sistem SIKAP-KI','Pertanyaan pengguna','Validasi, pencarian sumber, dan pemrosesan AI','Jawaban awal beserta sumber'],
    ['3','Masyarakat','Uraian barang/jasa','Mengisi data dan meminta rekomendasi kelas','Rekomendasi kelas dan langkah verifikasi'],
    ['4','Sistem SIKAP-KI','Hasil analisis','Menampilkan disclaimer, menyimpan log, dan rating','Riwayat dan monitoring'],
    ['5','Petugas Helpdesk KI','Konsultasi dieskalasi','Menelaah pertanyaan dan memberi arahan','Jawaban/tindak lanjut'],
    ['6','Admin/Pengelola KI','Dokumen/FAQ/regulasi','Memvalidasi, memperbarui, dan mengindeks sumber','Basis pengetahuan mutakhir'],
]: table += row(r)
extra += table + '</w:tbl>'
extra += para('6. Pengendalian dan Batasan', True, '22')
extra += para('Jawaban AI bersifat informatif dan menggunakan sumber yang telah diverifikasi. Pertanyaan yang memerlukan penilaian substantif dialihkan kepada petugas. Rekomendasi kelas merek bukan keputusan penerimaan merek. PDKI, SKM DJKI, dan sistem permohonan resmi menjadi rujukan final.')

with ZipFile(source) as zin, ZipFile(output, 'w', ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == 'word/document.xml':
            text = data.decode('utf-8')
            text = text.replace('</w:body>', extra + '</w:body>')
            data = text.encode('utf-8')
        zout.writestr(item, data)
print(output.resolve())
