let bridge = null;
let currentMode = 'documents';
let currentStatus = '';
let currentSearch = '';
let currentLocation = -1;

function updateTitle() {
  const pageTitle = document.getElementById('pageTitle');
  const pageDescription = document.getElementById('pageDescription');
  if (!pageTitle || !pageDescription) {
    return;
  }

  if (currentMode === 'archive') {
    pageTitle.textContent = 'Archiv';
    pageDescription.textContent = 'Archivierte Dokumente und Belege in personenzentrierter Dossieransicht.';
  } else {
    pageTitle.textContent = 'Dokumente';
    pageDescription.textContent = 'Personenzentrierte Dossieransicht mit Suche, Status und editierbaren Titeln.';
  }
}

async function refreshDocuments() {
  if (!bridge) {
    return;
  }
  bridge.list_documents(currentSearch, currentStatus, currentLocation, documents => {
    renderGroups(documents);
  });
}

function renderGroups(documents) {
  const groups = groupByPerson(documents);
  const container = document.getElementById('groups');
  container.innerHTML = '';

  Object.keys(groups).forEach(person => {
    const docs = groups[person];
    const template = document.getElementById('person-group-template');
    const group = template.content.cloneNode(true);
    const element = group.querySelector('.group');
    element.querySelector('.group-title').textContent = person;
    element.querySelector('.group-meta').textContent = `${docs.length} Dokument(e)`;
    element.querySelector('.group-count').textContent = String(docs.length);
    const documentsContainer = element.querySelector('.documents');

    docs.forEach(doc => {
      const rowTemplate = document.getElementById('document-row-template');
      const row = rowTemplate.content.cloneNode(true);
      const card = row.querySelector('.document-row');
      card.querySelector('.document-title').textContent = doc.title;
      card.querySelector('.document-reference').textContent = doc.reference;
      const badge = row.querySelector('.document-status');
      badge.textContent = doc.status;
      const renameButton = row.querySelector('.rename-button');
      renameButton.addEventListener('click', event => {
        event.stopPropagation();
        renameDocument(doc.id, doc.title);
      });
      card.addEventListener('click', () => {
        bridge.open_document(doc.id);
      });
      documentsContainer.appendChild(row);
    });

    container.appendChild(element);
  });
}

function groupByPerson(documents) {
  return documents.reduce((acc, item) => {
    const key = item.person_name || 'Nicht zugeordnet';
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(item);
    return acc;
  }, {});
}

function renameDocument(id, currentTitle) {
  const newTitle = window.prompt('Neue Dokumentbezeichnung', currentTitle);
  if (!newTitle || newTitle.trim() === '') {
    return;
  }
  bridge.rename_document(id, newTitle, result => {
    if (result) {
      refreshDocuments();
    } else {
      alert('Der Dokumenttitel konnte nicht aktualisiert werden.');
    }
  });
}

function setupFilters() {
  const search = document.getElementById('search');
  const statusFilter = document.getElementById('statusFilter');
  const locationFilter = document.getElementById('locationFilter');
  const reload = document.getElementById('reload');

  search.addEventListener('input', () => {
    currentSearch = search.value;
  });
  statusFilter.addEventListener('change', () => {
    currentStatus = statusFilter.value;
  });
  locationFilter.addEventListener('change', () => {
    currentLocation = Number(locationFilter.value);
  });
  reload.addEventListener('click', refreshDocuments);
}

function initializeLocations(locations) {
  const locationFilter = document.getElementById('locationFilter');
  locations.forEach(location => {
    const option = document.createElement('vscode-option');
    option.value = String(location.id);
    option.textContent = location.name;
    locationFilter.appendChild(option);
  });
}

function initialize() {
  new QWebChannel(qt.webChannelTransport, channel => {
    bridge = channel.objects.bridge;
    bridge.get_view_mode(mode => {
      currentMode = mode;
      updateTitle();
    });
    bridge.get_locations(locations => {
      initializeLocations(locations);
    });
    setupFilters();
    refreshDocuments();
  });
}

document.addEventListener('DOMContentLoaded', initialize);
