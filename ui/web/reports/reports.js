let bridge = null;

const REPORT_METRICS = [
  { id: 'applications', label: 'Anträge' },
  { id: 'evaluations', label: 'Prüfungen' },
  { id: 'approved', label: 'anspruchsberechtigte' },
  { id: 'rejected', label: 'abgelehnte' },
  { id: 'hardship', label: 'Härtefälle' },
  { id: 'cards', label: 'Kundenstamm pro Laden' },
];

function showMessage(text, type = 'info') {
  const message = document.getElementById('message');
  message.textContent = text;
  message.className = `message ${type}`;
}

function clearMessage() {
  const message = document.getElementById('message');
  message.textContent = '';
  message.className = 'message';
}

function getSelectedMetrics() {
  return REPORT_METRICS.filter(metric => {
    const checkbox = document.getElementById(`metric-${metric.id}`);
    return checkbox?.checked;
  }).map(metric => metric.id);
}

function setReportSummary(report) {
  document.getElementById('reportLocation').textContent = report.location_name;
  document.getElementById('reportPeriod').textContent = `${report.start_date} bis ${report.end_date}`;
}

function renderReport(report) {
  const selectedMetrics = getSelectedMetrics();
  const body = document.querySelector('#reportTable tbody');
  body.innerHTML = '';

  const rows = [];
  if (selectedMetrics.includes('applications')) {
    rows.push(['Anträge', report.total_applications]);
  }
  if (selectedMetrics.includes('evaluations')) {
    rows.push(['Prüfungen', report.total_evaluations]);
  }
  if (selectedMetrics.includes('approved')) {
    rows.push(['anspruchsberechtigte', report.approved_claims]);
  }
  if (selectedMetrics.includes('rejected')) {
    rows.push(['abgelehnte', report.rejected_claims]);
  }
  if (selectedMetrics.includes('hardship')) {
    rows.push(['Härtefälle', report.hardship_claims]);
  }

  if (rows.length === 0) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.setAttribute('colspan', '2');
    td.textContent = 'Bitte wählen Sie mindestens einen Parameter aus.';
    tr.appendChild(td);
    body.appendChild(tr);
  } else {
    rows.forEach(([label, value]) => {
      const tr = document.createElement('tr');
      const labelCell = document.createElement('td');
      const valueCell = document.createElement('td');
      labelCell.textContent = label;
      valueCell.textContent = value;
      tr.appendChild(labelCell);
      tr.appendChild(valueCell);
      body.appendChild(tr);
    });
  }

  const locationSection = document.getElementById('locationSection');
  const locationBody = document.querySelector('#locationTable tbody');
  locationBody.innerHTML = '';
  if (selectedMetrics.includes('cards') && report.cards_by_location && report.cards_by_location.length > 0) {
    locationSection.classList.remove('hidden');
    report.cards_by_location.forEach(item => {
      const tr = document.createElement('tr');
      const locationCell = document.createElement('td');
      const valueCell = document.createElement('td');
      locationCell.textContent = item.location_name || '-';
      valueCell.textContent = item.card_count || 0;
      tr.appendChild(locationCell);
      tr.appendChild(valueCell);
      locationBody.appendChild(tr);
    });
  } else {
    locationSection.classList.add('hidden');
  }
}

async function loadLocations() {
  const locationSelect = document.getElementById('locationSelect');
  locationSelect.innerHTML = '';
  const allOption = document.createElement('vscode-option');
  allOption.value = -1;
  allOption.textContent = 'Alle Standorte';
  locationSelect.appendChild(allOption);

  const locations = await bridge.get_locations();
  locations.forEach(location => {
    const option = document.createElement('vscode-option');
    option.value = location.id;
    option.textContent = location.name;
    locationSelect.appendChild(option);
  });
}

function getDateRange() {
  const startDate = document.getElementById('startDateInput').value;
  const endDate = document.getElementById('endDateInput').value;
  return { startDate, endDate };
}

function validateRange(startDate, endDate) {
  if (!startDate || !endDate) {
    showMessage('Bitte wählen Sie Start- und Enddatum aus.', 'error');
    return false;
  }
  if (startDate > endDate) {
    showMessage('Das Startdatum darf nicht nach dem Enddatum liegen.', 'error');
    return false;
  }
  return true;
}

async function loadReport() {
  clearMessage();
  const locationId = Number(document.getElementById('locationSelect').value || -1);
  const { startDate, endDate } = getDateRange();

  if (!validateRange(startDate, endDate)) {
    return;
  }

  const report = await bridge.get_period_report(locationId, startDate, endDate);
  setReportSummary(report);
  renderReport(report);
}

async function exportPdf() {
  clearMessage();
  const locationId = Number(document.getElementById('locationSelect').value || -1);
  const { startDate, endDate } = getDateRange();
  const selectedMetrics = getSelectedMetrics();

  if (!validateRange(startDate, endDate)) {
    return;
  }
  if (selectedMetrics.length === 0) {
    showMessage('Bitte wählen Sie mindestens einen Report-Parameter für den Export aus.', 'error');
    return;
  }

  const path = await bridge.export_report_pdf(locationId, startDate, endDate, selectedMetrics);
  if (path) {
    const url = `file:///${path.replace(/\\/g, '/')}`;
    window.open(url);
    showMessage('PDF wurde generiert und sollte nun geöffnet werden.', 'success');
  } else {
    showMessage('PDF konnte nicht erstellt werden.', 'error');
  }
}

async function exportExcel() {
  clearMessage();
  const locationId = Number(document.getElementById('locationSelect').value || -1);
  const { startDate, endDate } = getDateRange();
  const selectedMetrics = getSelectedMetrics();

  if (!validateRange(startDate, endDate)) {
    return;
  }
  if (selectedMetrics.length === 0) {
    showMessage('Bitte wählen Sie mindestens einen Report-Parameter für den Export aus.', 'error');
    return;
  }

  const path = await bridge.export_report_excel(locationId, startDate, endDate, selectedMetrics);
  if (path) {
    const url = `file:///${path.replace(/\\/g, '/')}`;
    window.open(url);
    showMessage('Excel-Datei wurde generiert und sollte nun geöffnet werden.', 'success');
  } else {
    showMessage('Excel-Datei konnte nicht erstellt werden.', 'error');
  }
}

function initializeDefaults() {
  const now = new Date();
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  document.getElementById('startDateInput').value = startOfMonth.toISOString().slice(0, 10);
  document.getElementById('endDateInput').value = now.toISOString().slice(0, 10);
}

function wireEvents() {
  document.getElementById('refreshButton').addEventListener('click', loadReport);
  document.getElementById('exportPdfButton').addEventListener('click', exportPdf);
  document.getElementById('exportExcelButton').addEventListener('click', exportExcel);
  REPORT_METRICS.forEach(metric => {
    const checkbox = document.getElementById(`metric-${metric.id}`);
    if (checkbox) {
      checkbox.addEventListener('change', loadReport);
    }
  });
}

new QWebChannel(qt.webChannelTransport, async (channel) => {
  bridge = channel.objects.bridge;
  initializeDefaults();
  await loadLocations();
  await loadReport();
  wireEvents();
});
