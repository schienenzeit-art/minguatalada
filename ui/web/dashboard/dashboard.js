let bridge = null;
const selectedKpi = { status: null };

function createBadgeElement(status) {
  const badge = document.createElement('vscode-badge');
  badge.setAttribute('pill', 'true');
  badge.textContent = status;
  const key = status.toLowerCase();
  if (key.includes('abgelehnt') || key.includes('abgelaufen')) {
    badge.classList.add('danger');
  } else if (key.includes('anspruchsberechtigt') || key.includes('härtefall')) {
    badge.classList.add('success');
  } else {
    badge.classList.add('warning');
  }
  return badge;
}

function renderKpiCards(items) {
  const container = document.getElementById('kpiGrid');
  container.innerHTML = '';
  items.forEach(item => {
    const template = document.getElementById('kpi-card-template');
    const card = template.content.cloneNode(true);
    const cardElement = card.querySelector('.kpi-card');
    cardElement.querySelector('.kpi-title').textContent = item.title;
    cardElement.querySelector('.kpi-value').textContent = item.value;
    cardElement.querySelector('.kpi-subtitle').textContent = item.subtitle;
    cardElement.addEventListener('click', () => {
      if (item.page) {
        bridge.navigate(item.page, item.filters || {});
      }
    });
    container.appendChild(cardElement);
  });
}

function renderClaims(claims) {
  const container = document.getElementById('claimsContainer');
  container.innerHTML = '';
  claims.forEach(claim => {
    const template = document.getElementById('claim-row-template');
    const card = template.content.cloneNode(true);
    const cardElement = card.querySelector('.claim-row');
    cardElement.querySelector('.claim-number').textContent = claim.case_number;
    cardElement.querySelector('.claim-person').textContent = claim.person_display_name;
    cardElement.querySelector('.claim-location').textContent = claim.location_name;
    cardElement.querySelector('.claim-date').textContent = claim.created_at;
    const badge = cardElement.querySelector('.claim-badge');
    badge.textContent = claim.status;
    if (claim.status.toLowerCase().includes('abgelehnt')) {
      badge.classList.add('danger');
    } else if (claim.status.toLowerCase().includes('anspruchsberechtigt') || claim.status.toLowerCase().includes('härtefall')) {
      badge.classList.add('success');
    } else {
      badge.classList.add('warning');
    }
    cardElement.addEventListener('click', () => {
      bridge.navigate('claims', { search_text: claim.case_number });
    });
    container.appendChild(cardElement);
  });
}

function onShowAllClicked() {
  bridge.navigate('claims', {});
}

function initialize() {
  const search = document.getElementById('search');
  const showAll = document.getElementById('showAll');
  showAll.addEventListener('click', onShowAllClicked);

  new QWebChannel(qt.webChannelTransport, channel => {
    bridge = channel.objects.bridge;
    bridge.get_kpi_items(items => {
      renderKpiCards(items);
    });
    bridge.get_recent_claims('', 5, claims => {
      claims.forEach(claim => {
        bridge.get_status_label(claim.status, statusLabel => {
          claim.status = statusLabel;
        });
      });
      renderClaims(claims);
    });
  });
}

document.addEventListener('DOMContentLoaded', initialize);
