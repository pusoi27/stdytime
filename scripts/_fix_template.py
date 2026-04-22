"""Reconstruct the HTML+JS section of student_form.html cleanly."""

NEW_HTML_JS = r"""
<div class="student-form-shell">
  <div class="student-form-hero">
    <h4>{{ action }} Student</h4>
  </div>

  <form method="post" id="studentForm" enctype="multipart/form-data">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

    <!-- Basic Information + Contact (combined) -->
    <div class="form-card">
      <div class="form-card-title"><span class="dot"></span>Basic Information</div>
      <div class="d-flex gap-3 align-items-start">
        <!-- Photo on left -->
        <input id="photoFileInput" name="photo" type="file" accept="image/jpeg,image/png,image/gif,image/webp" style="display:none;">
        <div class="photo-avatar-wrap" id="photoAvatarWrap" title="Click to upload photo">
          <div class="photo-avatar" id="photoAvatar">
            {% if student_photo %}
              <img id="photoPreviewImg" src="{{ url_for('static', filename='img/students/' + student_photo) }}" alt="Student photo">
            {% else %}
              <span class="photo-avatar-icon">&#128100;</span>
              <img id="photoPreviewImg" src="" alt="" style="display:none;">
            {% endif %}
            <div class="photo-avatar-overlay">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 9a2 2 0 012-2h.172a2 2 0 001.664-.89l.812-1.22A2 2 0 019.311 4h5.378a2 2 0 011.664.89l.812 1.22A2 2 0 0018.828 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
            </div>
          </div>
          <span class="photo-avatar-hint">Photo</span>
        </div>
        <!-- Name + Contact fields on right -->
        <div class="flex-grow-1">
          <div class="mb-2">
            <label for="name" class="form-label fw-semibold mb-1">Student Name <span class="required-star">*</span></label>
            <input id="name" name="name" class="form-control" value="{{ student[1] if student else '' }}" required placeholder="Full name">
          </div>
          <div class="row g-2">
            <div class="col-md-6">
              <label for="email" class="form-label fw-semibold mb-1">Email</label>
              <input id="email" name="email" type="email" class="form-control" value="{{ student[3] if student else '' }}">
            </div>
            <div class="col-md-6">
              <label for="phone" class="form-label fw-semibold mb-1">Phone</label>
              <input id="phone" name="phone" class="form-control" value="{{ student[4] if student else '' }}">
            </div>
          </div>
        </div>
      </div>
      <div class="mt-2 pt-2" style="border-top: 1px solid #f0f4ff;">
        <label class="form-label fw-semibold mb-1">Subjects <span class="required-star">*</span></label>
        <div id="subjectOptionsContainer" class="subject-options-wrap">
          <button type="button" id="addSubjectBtn" class="btn-add-subject-card"><span class="btn-add-subject-card-plus">+</span><span>Add Subject</span></button>
        </div>
        <div class="d-flex align-items-center flex-wrap gap-2 mt-2">
          <span class="small text-secondary">Study time:</span>
          <input type="number" id="sharedMinutesInput" class="form-control subject-time-shared" min="5" step="5" value="{{ (subject_rows[0].minutes if subject_rows and subject_rows[0].minutes else 30) }}">
          <span class="small text-muted">min per subject</span>
          <span class="study-summary" id="studySummary">Total study duration: 30 min</span>
        </div>
      </div>
    </div>

    <!-- Classification -->
    <div class="form-card">
      <div class="classification-title-wrap">
        <span class="classification-icon">&#8803;</span>
        <span>Classification</span>
      </div>
      <div class="row classification-grid">
        <div>
          <input class="classification-option" type="checkbox" name="el" id="assistedCheck" {% if student and student[9] %}checked{% endif %}>
          <label class="classification-label" for="assistedCheck">
            <div class="classification-card card-assisted">
              <div class="classification-radio"></div>
              <div class="classification-name">Assisted</div>
              <div class="classification-copy">Requires direct support</div>
            </div>
          </label>
        </div>
        <div>
          <input class="classification-option" type="checkbox" name="pi" id="monitoredCheck" {% if (student and student[10]) or (not student) or (student and not student[8] and not student[9] and not student[10] and not student[11]) %}checked{% endif %}>
          <label class="classification-label" for="monitoredCheck">
            <div class="classification-card card-monitored">
              <div class="classification-radio"></div>
              <div class="classification-name">Monitored</div>
              <div class="classification-copy">Periodic check-ins</div>
            </div>
          </label>
        </div>
        <div>
          <input class="classification-option" type="checkbox" name="paper_ws" id="independentCheck" {% if student and student[8] %}checked{% endif %}>
          <label class="classification-label" for="independentCheck">
            <div class="classification-card card-independent">
              <div class="classification-radio"></div>
              <div class="classification-name">Independent</div>
              <div class="classification-copy">Self-guided pace</div>
            </div>
          </label>
        </div>
        <div>
          <input class="classification-option" type="checkbox" name="v" id="virtualCheck" {% if student and student[11] %}checked{% endif %}>
          <label class="classification-label" for="virtualCheck">
            <div class="classification-card card-virtual">
              <div class="classification-radio"></div>
              <div class="classification-name">Virtual</div>
              <div class="classification-copy">100% remote learning</div>
            </div>
          </label>
        </div>
      </div>
    </div>

    <!-- Weekly Schedule -->
    <div class="form-card">
      <div class="form-card-title"><span class="dot"></span>Weekly Schedule</div>
      <input type="hidden" id="scheduleJsonInput" name="schedule_json" value="">
      <div class="day-picker-wrap" id="dayPickerWrap">
        {% if profile %}
          {% set days = [('Monday', 'monday'), ('Tuesday', 'tuesday'), ('Wednesday', 'wednesday'), ('Thursday', 'thursday'), ('Friday', 'friday'), ('Saturday', 'saturday'), ('Sunday', 'sunday')] %}
          {% for day_name, day_key in days %}
            {% if profile[day_key + '_start'] and profile[day_key + '_end'] %}
              <div class="day-card" data-day="{{ day_name }}">
                <div class="day-card-radio"></div>
                <span class="day-card-name">{{ day_name[:3] }}</span>
              </div>
            {% endif %}
          {% endfor %}
        {% endif %}
      </div>
    </div>

    <div class="sticky-actions d-flex flex-wrap gap-2 justify-content-end">
      <a href="{{ url_for('students_list') }}" class="btn btn-outline-secondary">Cancel</a>
      {% if from_calendar %}
        <a href="{{ url_for('center_calendar') }}" class="btn btn-outline-info">Back to Calendar</a>
      {% endif %}
      <button type="submit" class="btn btn-primary">{{ action }} Student</button>
    </div>
  </form>
</div>

<div id="subjectModalBackdrop" class="subject-modal-backdrop" aria-hidden="true">
  <div class="subject-modal" role="dialog" aria-modal="true" aria-labelledby="subjectModalTitle">
    <div class="subject-modal-header" id="subjectModalTitle">Add Subject</div>
    <div class="subject-modal-body">
      <label for="subjectModalInput" class="form-label">Subject name</label>
      <input id="subjectModalInput" type="text" class="form-control" placeholder="Enter subject name">
      <div class="form-text">Example: Science, Art, Coding</div>
    </div>
    <div class="subject-modal-footer">
      <button type="button" id="subjectModalCancel" class="btn btn-outline-secondary btn-sm">Cancel</button>
      <button type="button" id="subjectModalSave" class="btn btn-primary btn-sm">Save</button>
    </div>
  </div>
</div>

<script>
  const initialSubjectRows = {{ subject_rows | tojson }};
  const defaultSubjectOptions = ['Math', 'Reading', 'Writing'];

  const classHours = {
    {% if profile %}
      {% set days = [('Monday', 'monday'), ('Tuesday', 'tuesday'), ('Wednesday', 'wednesday'), ('Thursday', 'thursday'), ('Friday', 'friday'), ('Saturday', 'saturday'), ('Sunday', 'sunday')] %}
      {% for day_name, day_key in days %}
        {% if profile[day_key + '_start'] and profile[day_key + '_end'] %}
          '{{ day_name }}': { start: '{{ profile[day_key + "_start"] }}', end: '{{ profile[day_key + "_end"] }}' },
        {% endif %}
      {% endfor %}
    {% endif %}
  };

  const savedSchedule = {{ student_schedule | default([]) | tojson }};

  let availableSubjects = [];

  function normalizeKey(value) {
    return String(value || '').trim().toLowerCase();
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function getSharedMinutes() {
    const input = document.getElementById('sharedMinutesInput');
    return Math.max(5, Number(input ? input.value : 30) || 30);
  }

  function getSelectedSubjects() {
    return Array.from(document.querySelectorAll('input[name="subject_name[]"]:checked'))
      .map(function (input) { return String(input.value || '').trim(); })
      .filter(Boolean);
  }

  function getTotalStudyMinutes() {
    return getSelectedSubjects().length * getSharedMinutes();
  }

  function updateStudySummary() {
    const summary = document.getElementById('studySummary');
    if (summary) {
      summary.textContent = 'Total study duration: ' + getTotalStudyMinutes() + ' min';
    }
  }

  const subjectColorMap = { math: 'color-math', reading: 'color-reading', writing: 'color-writing' };

  function subjectColorClass(name) {
    return subjectColorMap[normalizeKey(name)] || 'color-custom';
  }

  function renderSubjectOptions(selectedSet) {
    const container = document.getElementById('subjectOptionsContainer');
    const addBtn = document.getElementById('addSubjectBtn');
    if (!container) return;

    container.querySelectorAll('.subject-card-wrap').forEach(function (el) { el.remove(); });

    availableSubjects.forEach(function (subjectName, index) {
      const safeId = 'subjectOption_' + index;
      const colorCls = subjectColorClass(subjectName);
      const isChecked = selectedSet.has(normalizeKey(subjectName));
      const wrapper = document.createElement('div');
      wrapper.className = 'subject-card-wrap';
      wrapper.innerHTML =
        '<input type="checkbox" class="subject-option-input" id="' + safeId + '" name="subject_name[]" value="' + escapeHtml(subjectName) + '" ' + (isChecked ? 'checked' : '') + '>' +
        '<label class="subject-card-label" for="' + safeId + '">' +
          '<div class="subject-card ' + colorCls + '">' +
            '<div class="subject-card-radio"></div>' +
            '<div class="subject-card-name">' + escapeHtml(subjectName) + '</div>' +
          '</div>' +
        '</label>' +
        '<button type="button" class="subject-card-remove" data-remove-subject="' + escapeHtml(subjectName) + '" aria-label="Remove ' + escapeHtml(subjectName) + '">\u00d7</button>';
      if (addBtn) {
        container.insertBefore(wrapper, addBtn);
      } else {
        container.appendChild(wrapper);
      }
    });

    updateStudySummary();
    refreshAllDayTimes();
  }

  function initSubjectsSection() {
    const optionsContainer = document.getElementById('subjectOptionsContainer');
    const addBtn = document.getElementById('addSubjectBtn');
    const sharedMinutesInput = document.getElementById('sharedMinutesInput');
    const modalBackdrop = document.getElementById('subjectModalBackdrop');
    const modalInput = document.getElementById('subjectModalInput');
    const modalSave = document.getElementById('subjectModalSave');
    const modalCancel = document.getElementById('subjectModalCancel');

    if (!optionsContainer) return;

    function closeSubjectModal() {
      if (!modalBackdrop) return;
      modalBackdrop.classList.remove('show');
      modalBackdrop.setAttribute('aria-hidden', 'true');
      if (modalInput) modalInput.value = '';
    }

    function openSubjectModal() {
      if (!modalBackdrop) return;
      modalBackdrop.classList.add('show');
      modalBackdrop.setAttribute('aria-hidden', 'false');
      if (modalInput) { modalInput.value = ''; modalInput.focus(); }
    }

    function saveSubjectFromModal() {
      const name = (modalInput ? modalInput.value : '').trim();
      if (!name) { if (modalInput) modalInput.focus(); return; }
      const key = normalizeKey(name);
      if (!availableSubjects.some(function (s) { return normalizeKey(s) === key; })) {
        availableSubjects.push(name.trim());
      }
      const selectedSet = new Set(
        Array.from(optionsContainer.querySelectorAll('input[name="subject_name[]"]')).filter(function (i) { return i.checked; }).map(function (i) { return normalizeKey(i.value); })
      );
      selectedSet.add(key);
      renderSubjectOptions(selectedSet);
      closeSubjectModal();
    }

    if (addBtn) addBtn.addEventListener('click', openSubjectModal);
    if (modalSave) modalSave.addEventListener('click', saveSubjectFromModal);
    if (modalCancel) modalCancel.addEventListener('click', closeSubjectModal);
    if (modalInput) {
      modalInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); saveSubjectFromModal(); }
      });
    }
    if (modalBackdrop) {
      modalBackdrop.addEventListener('click', function (e) {
        if (e.target === modalBackdrop) closeSubjectModal();
      });
    }
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modalBackdrop && modalBackdrop.classList.contains('show')) closeSubjectModal();
    });

    const seen = new Set();
    const initialSelectedSet = new Set();

    function registerSubject(rawName) {
      const name = String(rawName || '').trim();
      const key = normalizeKey(name);
      if (!key || seen.has(key)) return;
      seen.add(key);
      availableSubjects.push(name);
    }

    defaultSubjectOptions.forEach(registerSubject);

    const rows = Array.isArray(initialSubjectRows) ? initialSubjectRows : [];
    const hasExplicitSelectedFlag = rows.some(function (row) {
      return row && Object.prototype.hasOwnProperty.call(row, 'selected');
    });

    rows.forEach(function (row) {
      if (!row || !row.name) return;
      registerSubject(row.name);
      if (hasExplicitSelectedFlag) {
        if (row.selected) { initialSelectedSet.add(normalizeKey(row.name)); }
      } else if (String(row.name).trim()) {
        initialSelectedSet.add(normalizeKey(row.name));
      }
    });

    if (initialSubjectRows && initialSubjectRows.length > 0 && initialSubjectRows[0].minutes && sharedMinutesInput) {
      sharedMinutesInput.value = String(Math.max(5, Number(initialSubjectRows[0].minutes) || 30));
    }

    if (availableSubjects.length === 0) { defaultSubjectOptions.forEach(registerSubject); }
    if (initialSelectedSet.size === 0) { initialSelectedSet.add(normalizeKey('Math')); }

    renderSubjectOptions(initialSelectedSet);

    optionsContainer.addEventListener('change', function (e) {
      if (e.target && e.target.matches('input[name="subject_name[]"]')) {
        updateStudySummary();
        refreshAllDayTimes();
      }
    });

    optionsContainer.addEventListener('click', function (e) {
      const removeBtn = e.target.closest('.subject-card-remove');
      if (!removeBtn) return;
      const subjectName = removeBtn.dataset.removeSubject;
      if (!subjectName) return;
      availableSubjects = availableSubjects.filter(function (s) { return normalizeKey(s) !== normalizeKey(subjectName); });
      const currentSelected = new Set(getSelectedSubjects().map(normalizeKey));
      renderSubjectOptions(currentSelected);
    });

    if (sharedMinutesInput) {
      sharedMinutesInput.addEventListener('input', function () {
        updateStudySummary();
        refreshAllDayTimes();
      });
    }

    updateStudySummary();
  }

  function to12Hour(minutesSinceMidnight) {
    const h24 = Math.floor(minutesSinceMidnight / 60);
    const min = minutesSinceMidnight % 60;
    const ampm = h24 >= 12 ? 'PM' : 'AM';
    const h12 = h24 % 12 || 12;
    return h12 + ':' + String(min).padStart(2, '0') + ' ' + ampm;
  }

  function generateTimeSlots(startTime, endTime, offsetMinutes) {
    offsetMinutes = offsetMinutes || 30;
    const slots = [];
    const startParts = startTime.split(':').map(Number);
    const endParts = endTime.split(':').map(Number);
    let current = (startParts[0] * 60) + startParts[1];
    const end = (endParts[0] * 60) + endParts[1] - offsetMinutes;
    while (current <= end) {
      const h = Math.floor(current / 60);
      const m = current % 60;
      const value = String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
      slots.push({ value: value, display: to12Hour(current) });
      current += 30;
    }
    return slots;
  }

  // ── Multi-day schedule ──
  var selectedSchedule = {};
  savedSchedule.forEach(function(entry) {
    if (entry && entry.day) { selectedSchedule[entry.day] = entry.time || ''; }
  });

  function fillDayTimeSelect(selectEl, day, savedTime) {
    const offset = getTotalStudyMinutes();
    selectEl.innerHTML = '<option value="">-- Time --</option>';
    if (!classHours[day]) return;
    const slots = generateTimeSlots(classHours[day].start, classHours[day].end, offset);
    slots.forEach(function(slot) {
      const opt = document.createElement('option');
      opt.value = slot.value;
      opt.textContent = slot.display;
      if (savedTime && slot.value === savedTime) opt.selected = true;
      selectEl.appendChild(opt);
    });
  }

  function updateScheduleHidden() {
    const schedule = Object.keys(selectedSchedule).map(function(day) {
      return { day: day, time: selectedSchedule[day] };
    });
    const input = document.getElementById('scheduleJsonInput');
    if (input) input.value = JSON.stringify(schedule);
  }

  function refreshAllDayTimes() {
    document.querySelectorAll('#dayPickerWrap .day-card.day-selected').forEach(function(card) {
      const day = card.dataset.day;
      const sel = card.querySelector('.day-card-time');
      if (sel && classHours[day]) {
        const cur = sel.value;
        fillDayTimeSelect(sel, day, cur || selectedSchedule[day] || '');
      }
    });
  }

  function renderDayCards() {
    document.querySelectorAll('#dayPickerWrap .day-card').forEach(function(card) {
      const day = card.dataset.day;
      const isSelected = Object.prototype.hasOwnProperty.call(selectedSchedule, day);
      card.classList.toggle('day-selected', isSelected);
      var sel = card.querySelector('.day-card-time');
      if (!sel) {
        sel = document.createElement('select');
        sel.className = 'day-card-time form-select form-select-sm';
        card.appendChild(sel);
      }
      if (isSelected) {
        sel.style.display = '';
        fillDayTimeSelect(sel, day, selectedSchedule[day] || '');
        sel.onchange = (function(d, s) {
          return function() { selectedSchedule[d] = s.value; updateScheduleHidden(); };
        })(day, sel);
      } else {
        sel.style.display = 'none';
      }
    });
    updateScheduleHidden();
  }

  function initDayPicker() {
    const wrap = document.getElementById('dayPickerWrap');
    if (!wrap) return;
    wrap.addEventListener('click', function(e) {
      const card = e.target.closest('.day-card');
      if (!card) return;
      const sel = card.querySelector('.day-card-time');
      if (sel && (e.target === sel || sel.contains(e.target))) return;
      const day = card.dataset.day;
      if (Object.prototype.hasOwnProperty.call(selectedSchedule, day)) {
        delete selectedSchedule[day];
      } else {
        selectedSchedule[day] = '';
      }
      renderDayCards();
    });
    renderDayCards();
  }

  function initExclusiveClassification() {
    const options = Array.from(document.querySelectorAll('.classification-option'));
    const defaultOption = document.getElementById('monitoredCheck');

    function keepOnly(checkedOption) {
      options.forEach(function(option) { option.checked = option === checkedOption; });
    }

    options.forEach(function(option) {
      option.addEventListener('change', function () {
        if (this.checked) { keepOnly(this); return; }
        const anyChecked = options.some(function(o) { return o.checked; });
        if (!anyChecked && defaultOption) { defaultOption.checked = true; }
      });
    });

    const checked = options.filter(function(o) { return o.checked; });
    if (checked.length === 0 && defaultOption) {
      defaultOption.checked = true;
    } else if (checked.length > 1) {
      const priority = [
        document.getElementById('monitoredCheck'),
        document.getElementById('assistedCheck'),
        document.getElementById('independentCheck'),
        document.getElementById('virtualCheck')
      ].filter(Boolean);
      const chosen = priority.find(function(p) { return p.checked; }) || checked[0];
      keepOnly(chosen);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const photoWrap = document.getElementById('photoAvatarWrap');
    const photoInput = document.getElementById('photoFileInput');
    const photoPreview = document.getElementById('photoPreviewImg');
    const photoAvatar = document.getElementById('photoAvatar');

    if (photoWrap && photoInput) {
      photoWrap.addEventListener('click', function () { photoInput.click(); });
      photoInput.addEventListener('change', function () {
        const file = photoInput.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function (e) {
          const icon = photoAvatar.querySelector('.photo-avatar-icon');
          if (icon) icon.style.display = 'none';
          if (photoPreview) { photoPreview.src = e.target.result; photoPreview.style.display = ''; }
        };
        reader.readAsDataURL(file);
      });
    }

    initSubjectsSection();
    initDayPicker();
    initExclusiveClassification();

    document.getElementById('studentForm').addEventListener('submit', function (e) {
      updateScheduleHidden();
      const selectedSubjects = getSelectedSubjects();
      if (selectedSubjects.length === 0) {
        e.preventDefault();
        alert('Please select at least one subject.');
        return;
      }
      const mins = String(getSharedMinutes());
      const form = document.getElementById('studentForm');
      selectedSubjects.forEach(function () {
        const inp = document.createElement('input');
        inp.type = 'hidden';
        inp.name = 'subject_minutes[]';
        inp.value = mins;
        form.appendChild(inp);
      });
    });
  });
</script>
{% endblock %}"""

with open('templates/student_form.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the </style> tag - take everything up to and including it, then append new HTML+JS
style_end = content.find('</style>')
if style_end == -1:
    print("ERROR: </style> not found!")
    exit(1)

css_section = content[:style_end + len('</style>')]

# Remove any duplicate/old day-selected CSS that was added inside the style tag
# (clean up the duplicate day-selected-1/2 CSS and old day-time-group CSS)
# These are now replaced by the single .day-selected rule above the </style>
OLD_CSS_BLOCK = """  .day-card.day-selected-1 {
    background: #dbeafe;
    border-color: #3b82f6;
    box-shadow: 0 0 0 1px rgba(59,130,246,0.2), 0 4px 12px rgba(59,130,246,0.12);
  }
  .day-card.day-selected-1 .day-card-radio {
    border-color: #3b82f6;
  }
  .day-card.day-selected-1 .day-card-radio::after {
    content: '';
    position: absolute;
    inset: 2px;
    border-radius: 50%;
    background: #3b82f6;
  }

  .day-card.day-selected-2 {
    background: #d1fae5;
    border-color: #22c55e;
    box-shadow: 0 0 0 1px rgba(34,197,94,0.2), 0 4px 12px rgba(34,197,94,0.12);
  }
  .day-card.day-selected-2 .day-card-radio {
    border-color: #22c55e;
  }
  .day-card.day-selected-2 .day-card-radio::after {
    content: '';
    position: absolute;
    inset: 2px;
    border-radius: 50%;
    background: #22c55e;
  }

  .day-time-select-wrap {
    margin-top: 0.5rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .day-time-group {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .day-time-group label {
    font-size: 0.82rem;
    font-weight: 600;
    color: #395b95;
    white-space: nowrap;
    margin: 0;
  }"""

NEW_CSS_BLOCK = """  .day-card.day-selected {
    background: #dbeafe;
    border-color: #3b82f6;
    box-shadow: 0 0 0 1px rgba(59,130,246,0.2), 0 4px 12px rgba(59,130,246,0.12);
  }
  .day-card.day-selected .day-card-radio {
    border-color: #3b82f6;
  }
  .day-card.day-selected .day-card-radio::after {
    content: '';
    position: absolute;
    inset: 2px;
    border-radius: 50%;
    background: #3b82f6;
  }
  .day-card-time {
    font-size: 0.76rem;
    padding: 0.15rem 0.3rem !important;
    min-width: 85px;
    border-radius: 8px !important;
    border: 1px solid #93c5fd !important;
    background: #fff;
    cursor: pointer;
    margin-top: 0.3rem;
  }"""

if OLD_CSS_BLOCK in css_section:
    css_section = css_section.replace(OLD_CSS_BLOCK, NEW_CSS_BLOCK)
    print("CSS block replaced OK")
else:
    print("WARNING: OLD_CSS_BLOCK not found exactly — CSS section left as-is")

new_content = css_section + '\n' + NEW_HTML_JS

with open('templates/student_form.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Written")
print(f"Total lines: {len(new_content.splitlines())}")
