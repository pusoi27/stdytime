# routes/qr.py
import os
import io
import sqlite3
from flask import render_template, request, jsonify, send_file
from modules import student_manager, assistant_manager, qr_generator
from modules.database import DB_PATH
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

def register_qr_routes(app):
    """Register QR code generation and printing routes."""
    
    # ================================================================
    # QR Code Generation - Students
    # ================================================================
    
    @app.route("/qr/generate")
    def qr_generate():
        """Generate QR code for a specific student."""
        students = student_manager.get_all_students()
        return render_template("qr_generate.html", students=students)

    @app.route("/qr/generate/<int:sid>", methods=["POST", "GET"])
    def qr_generate_student(sid):
        """Generate and return QR code PNG for a student."""
        student = student_manager.get_student(sid)
        if not student:
            return "Student not found", 404
        qr_data = f"ID:{student[0]}\nName:{student[1]}"
        path = qr_generator.generate_qr(qr_data, f"student_{student[0]}")
        return send_file(path, mimetype='image/png')

    @app.route("/qr/generate_all", methods=["POST"])
    def qr_generate_all():
        """Generate QR codes for all students where missing."""
        students = student_manager.get_all_students()
        generated = []
        skipped = []
        errors = []
        out_dir = os.path.join('assets', 'qr_codes')
        os.makedirs(out_dir, exist_ok=True)
        for s in students:
            try:
                sid = s[0]
                name = f"student_{sid}"
                dest = os.path.join(out_dir, f"{name}.png")
                if os.path.exists(dest):
                    skipped.append(name + '.png')
                    continue
                qr_data = f"ID:{sid}\nName:{s[1]}"
                path = qr_generator.generate_qr(qr_data, name)
                generated.append(os.path.basename(path))
            except Exception as e:
                errors.append({'id': sid, 'error': str(e)})
        return jsonify({'generated': generated, 'skipped': skipped, 'errors': errors, 'generated_count': len(generated), 'skipped_count': len(skipped)})

    @app.route('/assets/qr_codes/<path:filename>')
    def serve_qr_code(filename):
        """Serve generated QR code images from assets/qr_codes folder."""
        qr_dir = os.path.join(os.getcwd(), 'assets', 'qr_codes')
        from flask import send_from_directory
        return send_from_directory(qr_dir, filename)

    # ================================================================
    # QR Code Generation - Assistants
    # ================================================================

    @app.route("/qr/assistants/generate_all", methods=["POST"])
    def qr_assistants_generate_all():
        """Generate QR codes for all assistants where missing."""
        assistants = assistant_manager.get_all_assistants()
        generated, skipped, errors = [], [], []
        out_dir = os.path.join('assets', 'qr_codes')
        os.makedirs(out_dir, exist_ok=True)
        for a in assistants:
            aid = a[0]
            name = a[1]
            qr_name = f"assistant_{aid}"
            dest = os.path.join(out_dir, f"{qr_name}.png")
            if os.path.exists(dest):
                skipped.append(qr_name + '.png')
                continue
            try:
                qr_data = f"ASST:{aid}\nName:{name}"
                path = qr_generator.generate_qr(qr_data, qr_name)
                generated.append(os.path.basename(path))
            except Exception as e:
                errors.append({'id': aid, 'error': str(e)})
        return jsonify({'generated': generated, 'skipped': skipped, 'errors': errors})

    @app.route("/qr/assistants/generate/<int:aid>", methods=["POST"])
    def qr_assistant_generate(aid):
        """Generate QR code for a single assistant."""
        assistant = assistant_manager.get_assistant(aid)
        if not assistant:
            return "Assistant not found", 404
        out_dir = os.path.join('assets', 'qr_codes')
        os.makedirs(out_dir, exist_ok=True)
        qr_name = f"assistant_{aid}"
        dest = os.path.join(out_dir, f"{qr_name}.png")
        if os.path.exists(dest):
            return jsonify({'message': 'exists', 'file': os.path.basename(dest)})
        qr_data = f"ASST:{aid}\nName:{assistant[1]}"
        path = qr_generator.generate_qr(qr_data, qr_name)
        return jsonify({'message': 'generated', 'file': os.path.basename(path)})

    # ================================================================
    # QR Code Generation - Books
    # ================================================================

    @app.route("/qr/books/generate_all", methods=["POST"])
    def qr_books_generate_all():
        """Generate QR codes for all books where missing."""
        generated, skipped, errors = [], [], []
        out_dir = os.path.join('assets', 'qr_codes')
        os.makedirs(out_dir, exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id, title FROM books ORDER BY title")
            for (bid, title) in c.fetchall():
                try:
                    qr_name = f"book_{bid}"
                    dest = os.path.join(out_dir, f"{qr_name}.png")
                    if os.path.exists(dest):
                        skipped.append(qr_name + '.png')
                        continue
                    qr_data = f"BOOK:{bid}\nTitle:{title or ''}"
                    path = qr_generator.generate_qr(qr_data, qr_name)
                    generated.append(os.path.basename(path))
                except Exception as e:
                    errors.append({'id': bid, 'error': str(e)})
        return jsonify({'generated': generated, 'skipped': skipped, 'errors': errors})

    @app.route("/qr/books/generate/<int:bid>", methods=["POST"])
    def qr_book_generate(bid):
        """Generate QR code for a single book."""
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            row = c.execute("SELECT id, title FROM books WHERE id=?", (bid,)).fetchone()
        if not row:
            return jsonify({"error": "Book not found"}), 404
        out_dir = os.path.join('assets', 'qr_codes')
        os.makedirs(out_dir, exist_ok=True)
        qr_name = f"book_{bid}"
        dest = os.path.join(out_dir, f"{qr_name}.png")
        if os.path.exists(dest):
            return jsonify({'message': 'exists', 'file': os.path.basename(dest)})
        qr_data = f"BOOK:{bid}\nTitle:{row[1] or ''}"
        path = qr_generator.generate_qr(qr_data, qr_name)
        return jsonify({'message': 'generated', 'file': os.path.basename(path)})

    # ================================================================
    # QR Code PDF Generation
    # ================================================================

    @app.route('/qr/pdf/individual/<int:sid>')
    def qr_pdf_individual(sid):
        """Generate Avery 8160 PDF for a single student."""
        student = student_manager.get_student(sid)
        if not student:
            return "Student not found", 404
        qr_path = os.path.join(os.getcwd(), 'assets', 'qr_codes', f'student_{sid}.png')
        labels = [{'name': student[1], 'qr_path': qr_path}]
        buf = _build_avery_pdf(labels)
        filename = f'student_{sid}_labels.pdf'
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=filename)

    @app.route('/qr/pdf/all')
    def qr_pdf_all():
        """Generate Avery 8160 PDF for all students."""
        students = student_manager.get_all_students()
        labels = []
        for s in students:
            sid = s[0]
            qr_path = os.path.join(os.getcwd(), 'assets', 'qr_codes', f'student_{sid}.png')
            labels.append({'name': s[1], 'qr_path': qr_path if os.path.exists(qr_path) else None})
        buf = _build_avery_pdf(labels)
        filename = 'students_qr_labels.pdf'
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=filename)

    @app.route('/qr/assistants/pdf')
    def qr_assistants_pdf():
        """Generate Avery 8163 PDF for assistants with existing QR codes."""
        assistants = assistant_manager.get_all_assistants()
        labels = []
        qr_dir = os.path.join('assets', 'qr_codes')
        for a in assistants:
            aid = a[0]
            qr_path = os.path.join(qr_dir, f"assistant_{aid}.png")
            if os.path.exists(qr_path):
                labels.append({'name': a[1], 'qr_path': qr_path})
        if not labels:
            return "No assistant QR codes found. Generate them first.", 400
        pdf_buffer = _build_avery8163_pdf(labels)
        return send_file(pdf_buffer, as_attachment=True, download_name="assistant_qr_avery8163.pdf", mimetype='application/pdf')

    @app.route('/qr/assistants/pdf/individual/<int:aid>')
    def qr_assistant_pdf_individual(aid):
        """Generate Avery 8163 PDF for a single assistant."""
        assistant = assistant_manager.get_assistant(aid)
        if not assistant:
            return "Assistant not found", 404
        qr_path = os.path.join('assets', 'qr_codes', f"assistant_{aid}.png")
        if not os.path.exists(qr_path):
            return "QR code not found. Generate it first.", 400
        labels = [{'name': assistant[1], 'qr_path': qr_path}]
        pdf_buffer = _build_avery8163_pdf(labels)
        return send_file(pdf_buffer, as_attachment=True, download_name=f"assistant_{aid}_qr.pdf", mimetype='application/pdf')

    @app.route('/qr/books/pdf')
    def qr_books_pdf():
        """Generate Avery 8163 PDF for all books with existing QR codes."""
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id, title FROM books ORDER BY title")
            books = c.fetchall()
        labels = []
        qr_dir = os.path.join('assets', 'qr_codes')
        for b in books:
            bid = b[0]
            qr_path = os.path.join(qr_dir, f"book_{bid}.png")
            if os.path.exists(qr_path):
                labels.append({'name': b[1], 'qr_path': qr_path})
        if not labels:
            return "No book QR codes found. Generate them first.", 400
        pdf_buffer = _build_avery8163_pdf(labels)
        return send_file(pdf_buffer, as_attachment=True, download_name="books_qr_avery8163.pdf", mimetype='application/pdf')

    @app.route('/qr/books/pdf/individual/<int:bid>')
    def qr_book_pdf_individual(bid):
        """Generate PDF for a single book QR."""
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            row = c.execute("SELECT id, title FROM books WHERE id=?", (bid,)).fetchone()
        if not row:
            return "Book not found", 404
        qr_path = os.path.join('assets', 'qr_codes', f"book_{bid}.png")
        if not os.path.exists(qr_path):
            return "QR code not found. Generate it first.", 400
        labels = [{'name': row[1], 'qr_path': qr_path}]
        pdf_buffer = _build_avery8163_pdf(labels)
        return send_file(pdf_buffer, as_attachment=True, download_name=f"book_{bid}_qr.pdf", mimetype='application/pdf')

    # ================================================================
    # QR Code Print Pages
    # ================================================================

    @app.route("/qr/print/individual")
    def qr_print_individual():
        """Page to select a student and print their QR code."""
        students = student_manager.get_all_students()
        return render_template("qr_print_individual.html", students=students)

    @app.route("/qr/print/all")
    def qr_print_all():
        """Generate and display QR codes for all active students."""
        students = student_manager.get_all_students()
        active_students = [s for s in students if len(s) >= 8 and s[7] == 1]
        return render_template("qr_print_all.html", students=active_students)

    @app.route("/qr/generate_page")
    def qr_generate_page():
        """Display unified QR generation page for students, assistants, and books."""
        students = student_manager.get_all_students()
        assistants = assistant_manager.get_all_assistants()
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id, title FROM books ORDER BY title")
            books = c.fetchall()
        return render_template("qr_generate_all.html", students=students, assistants=assistants, books=books)

    @app.route("/qr/print_page")
    def qr_print_page():
        """Display unified QR print page for students, assistants, and books."""
        students = student_manager.get_all_students()
        assistants = assistant_manager.get_all_assistants()
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id, title FROM books ORDER BY title")
            books = c.fetchall()
        return render_template("qr_print_all.html", students=students, assistants=assistants, books=books)


def _build_avery_pdf(labels):
    """Build PDF for Avery 8160 (1" x 2.625" labels, 3 columns x 10 rows per page)."""
    buffer = io.BytesIO()
    page_width, page_height = letter  # portrait
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

    cols = 3
    rows = 10
    label_w = 2.625 * inch
    label_h = 1.0 * inch
    left_margin = 0.219 * inch
    top_margin = 0.5 * inch
    qr_size = 0.8 * inch

    labels_per_page = cols * rows
    total = len(labels)
    pages = (total + labels_per_page - 1) // labels_per_page or 1

    idx = 0
    for p in range(pages):
        for r in range(rows):
            for c_idx in range(cols):
                x = left_margin + c_idx * label_w
                y = page_height - top_margin - (r + 1) * label_h
                if idx < total:
                    lab = labels[idx]
                    c.rect(x, y, label_w, label_h, stroke=0, fill=0)
                    padding = 0.06 * inch
                    qr_x = x + padding
                    qr_y = y + (label_h - qr_size) / 2
                    name_x = qr_x + qr_size + (0.08 * inch)
                    name_width = label_w - (qr_size + padding + 0.08 * inch + padding)

                    if lab.get('qr_path') and os.path.exists(lab['qr_path']):
                        try:
                            c.drawImage(lab['qr_path'], qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True, mask='auto')
                        except Exception:
                            pass

                    name = (lab.get('name') or '')
                    font_size = 11
                    c.setFont('Helvetica-Bold', font_size)
                    while c.stringWidth(name, 'Helvetica-Bold', font_size) > name_width and font_size > 5:
                        font_size -= 1
                        c.setFont('Helvetica-Bold', font_size)
                    text_y = y + (label_h - font_size) / 2 - 1
                    max_chars = int((name_width / c.stringWidth('W', 'Helvetica-Bold', font_size)) * 1)
                    if max_chars > 3 and len(name) > max_chars:
                        name = name[:max_chars-3] + '...'
                    c.drawString(name_x, text_y, name)
                else:
                    pass
                idx += 1
        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


def _build_avery8163_pdf(labels):
    """Build PDF for Avery 8163 (2" x 4" labels, 2 columns x 5 rows per page)."""
    buffer = io.BytesIO()
    page_width, page_height = letter  # portrait
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

    cols = 2
    rows = 5
    label_w = 4.0 * inch
    label_h = 2.0 * inch
    left_margin = 0.5 * inch
    top_margin = 0.5 * inch
    qr_size = 1.4 * inch

    labels_per_page = cols * rows
    total = len(labels)
    pages = (total + labels_per_page - 1) // labels_per_page or 1

    idx = 0
    for _ in range(pages):
        for r in range(rows):
            for col in range(cols):
                if idx >= total:
                    break
                label = labels[idx]
                x = left_margin + col * label_w
                y = page_height - top_margin - (r + 1) * label_h

                c.setStrokeColorRGB(0.85, 0.85, 0.85)
                c.rect(x, y, label_w, label_h, stroke=1, fill=0)

                if label.get("qr_path") and os.path.exists(label.get("qr_path")):
                    c.drawImage(label.get("qr_path"), x + 0.2 * inch, y + (label_h - qr_size) / 2, qr_size, qr_size, preserveAspectRatio=True)

                c.setFont("Helvetica-Bold", 14)
                c.drawString(x + qr_size + 0.4 * inch, y + label_h / 2 + 4, label.get("name", ""))
                idx += 1
        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer
