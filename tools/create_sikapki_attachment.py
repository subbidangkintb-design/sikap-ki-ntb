from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape
from pathlib import Path

OUT = Path('Lampiran_Flowchart_Proses_Bisnis_SIKAP-KI_NTB.docx')

def p(text='', style=None):
    sty = f'<w:pStyle w:val="{style}"/>' if style else ''
    return f'<w:p><w:pPr>{sty}</w:pPr><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

def table(rows):
    xml = '<w:tbl><w:tblPr><w:tblBorders>' + ''.join(
        f'<w:{x} w:val="single" w:sz="4" w:space="0" w:color="808080"/>' for x in ('top','left','bottom','right','insideH','insideV')
    ) + '</w:tblBorders></w:tblPr>'
    for row in rows:
        xml += '<w:tr>'
        for cell in row:
            xml += f'<w:tc><w:p><w:r><w:t xml:space="preserve">{escape(cell)}</w:t></w:r></w:p></w:tc>'
        xml += '</w:tr>'
    return xml + '</w:tbl>'

content = []
content += [p('LAMPIRAN TAMBAHAN', 'Title'), p('FLOWCHART DAN PROSES BISNIS SIKAP-KI NTB', 'Title')]
content += [p('Lampiran ini menjadi bahan penelaahan dan verifikasi teknis. SIKAP-KI adalah kanal informasi dan konsultasi awal; keputusan hukum dan pemeriksaan resmi tetap menjadi kewenangan DJKI.')]
content += [p('1. Flowchart Umum Layanan', 'Heading1')]
content += [p('MULAI -> Pengguna membuka website -> Memilih layanan (Chatbot / Cek Kelas Merek / FAQ / Checklist) -> Mengisi pertanyaan atau data -> Sistem memvalidasi input -> Sistem memproses menggunakan basis pengetahuan dan/atau AI -> Hasil awal ditampilkan beserta sumber dan batasan -> [Perlu pendalaman?] Jika TIDAK: SELESAI. Jika YA: konsultasi diteruskan ke petugas -> Petugas memberi arahan -> Status diperbarui -> SELESAI.')]
content += [p('2. Flowchart Chatbot Helpdesk KI', 'Heading1')]
content += [p('MULAI -> Pengguna mengetik pertanyaan -> Sistem memeriksa konteks -> Sistem mencari dokumen/FAQ resmi yang relevan -> [Konteks cukup?] Jika YA: AI menyusun jawaban berbasis sumber -> Jawaban dan sumber ditampilkan -> Rating pengguna -> SELESAI. Jika TIDAK: sistem membuat ID pelacakan -> pertanyaan diterima petugas -> petugas menindaklanjuti -> status diperbarui -> SELESAI.')]
content += [p('3. Flowchart Asisten Penelusuran Kelas Merek', 'Heading1')]
content += [p('MULAI -> Pengguna memasukkan nama merek dan uraian barang/jasa -> Sistem memvalidasi data -> Sistem mencocokkan uraian dengan Nice Classification -> AI menyusun maksimal tiga rekomendasi kelas -> [Uraian ambigu?] Jika YA: sistem meminta klarifikasi dan proses diulang. Jika TIDAK: hasil, disclaimer, dan tautan PDKI/SKM ditampilkan -> log anonim disimpan -> SELESAI.')]
content += [p('4. Flowchart Pengelolaan Basis Pengetahuan', 'Heading1')]
content += [p('Petugas mengunggah dokumen/FAQ -> Admin memeriksa sumber dan isi -> [Valid?] Jika TIDAK: dikembalikan untuk perbaikan. Jika YA: status terverifikasi -> teks dipecah menjadi potongan -> embedding dibuat -> indeks pencarian diperbarui -> sumber aktif digunakan chatbot -> SELESAI.')]
content += [p('5. Proses Bisnis Utama', 'Heading1')]
content += [table([
    ['No.', 'Aktor', 'Input', 'Proses', 'Output'],
    ['1', 'Masyarakat', 'Pertanyaan/kebutuhan KI', 'Mengakses layanan dan mengirim pertanyaan', 'Permintaan tercatat'],
    ['2', 'Sistem SIKAP-KI', 'Pertanyaan pengguna', 'Validasi, pencarian sumber, dan pemrosesan AI', 'Jawaban awal beserta sumber'],
    ['3', 'Masyarakat', 'Uraian barang/jasa merek', 'Mengisi data dan meminta rekomendasi kelas', 'Rekomendasi kelas dan langkah verifikasi'],
    ['4', 'Sistem SIKAP-KI', 'Hasil analisis', 'Menampilkan disclaimer, menyimpan log, dan menyediakan rating', 'Riwayat dan data monitoring'],
    ['5', 'Petugas Helpdesk KI', 'Konsultasi yang dieskalasi', 'Menelaah pertanyaan dan memberi arahan', 'Jawaban/tindak lanjut petugas'],
    ['6', 'Admin/Pengelola KI', 'Dokumen, FAQ, regulasi', 'Memvalidasi, memperbarui, dan mengindeks sumber', 'Basis pengetahuan mutakhir'],
])]
content += [p('6. Pengendalian dan Batasan', 'Heading1')]
content += [p('1) Jawaban AI bersifat informatif dan menggunakan sumber yang telah diverifikasi. 2) Pertanyaan yang tidak cukup konteks atau memerlukan penilaian substantif dialihkan kepada petugas. 3) Rekomendasi kelas merek bukan keputusan penerimaan merek. 4) PDKI, SKM DJKI, dan sistem permohonan resmi menjadi rujukan final. 5) Data dan basis pengetahuan dikelola oleh pengguna berwenang.')]

body = ''.join(content) + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1200" w:right="1200" w:bottom="1200" w:left="1200"/></w:sectPr>'
document = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>'''
styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="20"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:jc w:val="center"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="Heading 1"/><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style></w:styles>'''
types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
docrels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''

with ZipFile(OUT, 'w', ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', types)
    z.writestr('_rels/.rels', rels)
    z.writestr('word/_rels/document.xml.rels', docrels)
    z.writestr('word/document.xml', document)
    z.writestr('word/styles.xml', styles)
print(OUT.resolve())
