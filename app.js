
    let results = [];
    let currentProvider = 'anthropic';

    let isProcessing = false;
    let activeSupplier = 'signes';
    const supplierState = {
      signes: { results: [], pendingData: null, description: 'Catálogo activo: Signes · formato de Excel actual' },
      dcasa: { results: [], pendingData: null, description: 'Catálogo activo: DCasa · formato de Excel pendiente de configurar' },
      minerales: { results: [], pendingData: null, description: 'Catálogo activo: Minerales · formato de Excel pendiente de configurar' },
      trediser: { results: [], pendingData: null, description: 'Catálogo activo: Trediser · formato de Excel pendiente de configurar' }
    };

    function switchSupplier(supplier) {
      if (isProcessing || supplier === activeSupplier) return;
      supplierState[activeSupplier].results = results;
      supplierState[activeSupplier].pendingData = window.pendingData || null;
      supplierState[activeSupplier].urls = $('urlsInput').value;
      activeSupplier = supplier;
      $('urlsInput').value = supplierState[supplier].urls || ''; 
      results = supplierState[supplier].results || [];
      window.pendingData = supplierState[supplier].pendingData || null;
      document.querySelectorAll('.supplier-tab').forEach(tab => {
        const selected = tab.id === `supplier-tab-${supplier}`;
        tab.classList.toggle('active', selected);
        tab.setAttribute('aria-selected', selected ? 'true' : 'false');
      });
      $('supplierDescription').textContent = supplierState[supplier].description;
      $('resultsBody').innerHTML = '';
      $('resultsContainer').classList.toggle('hidden', results.length === 0);
      $('exportGroup').classList.toggle('hidden', results.length === 0);
      results.forEach((item, index) => {
        addRow(index, item);
        if (item.error) setRowError(index, item.error, item.material, item.color, item.medidas);
        else setRowSuccess(index, item.title, item.highlights, item.material, item.color, item.medidas, item.bullet_points, item.description, item.backend_keywords);
      });
      $('resultsCount').textContent = results.length;
      $('retryBtn').classList.toggle('hidden', !results.some(r => r.error));
      updateSupplierCounts();
      updateResultsSummary();
    }

    function updateSupplierCounts() {
      Object.keys(supplierState).forEach(supplier => {
        const count = supplier === activeSupplier ? results.length : supplierState[supplier].results.length;
        if ($(`supplier-count-${supplier}`)) $(`supplier-count-${supplier}`).textContent = count;
      });
    }

    const PROVIDERS = {
      anthropic: {
        label: 'Anthropic (console.anthropic.com)',
        placeholder: 'sk-ant-api03-…',
        hint: 'Requiere créditos de pago en console.anthropic.com',
        storageKey: 'apikey_anthropic',
      },
      openai: {
        label: 'OpenAI (platform.openai.com)',
        placeholder: 'sk-proj-…',
        hint: 'Requiere créditos en platform.openai.com',
        storageKey: 'apikey_openai',
      },
      gemini: {
        label: 'Google AI Studio (Gemini 2.5 Flash)',
        placeholder: 'AIza…',
        hint: 'Introduce tu clave. En local también puedes configurarla en el servidor.',
        storageKey: 'apikey_gemini',
      },
      qwen: {
        label: 'Alibaba DashScope (dashscope.console.aliyun.com)',
        placeholder: 'sk-…',
        hint: 'Modelo Qwen3-VL Plus. Requiere créditos en DashScope.',
        storageKey: 'apikey_qwen',
      },
      groq: {
        label: 'Groq Cloud (console.groq.com)',
        placeholder: 'gsk_…',
        hint: 'Modelo Llama-3.2 / Scout Vision. ¡Súper rápido!',
        storageKey: 'apikey_groq',
      },
      kimi: {
        label: 'Moonshot AI Kimi (platform.moonshot.cn)',
        placeholder: 'sk-…',
        hint: 'Modelo Kimi-Vision. Requiere créditos o prueba gratuita.',
        storageKey: 'apikey_kimi',
      },
      deepseek: {
        label: 'DeepSeek Platform (platform.deepseek.com)',
        placeholder: 'sk-…',
        hint: 'Capa de créditos al registrarse.',
        storageKey: 'apikey_deepseek',
      },
      openrouter: {
        label: 'OpenRouter (openrouter.ai)',
        placeholder: 'sk-or-v1-…',
        hint: 'Usa DeepSeek V4 Flash Vision a través de OpenRouter.',
        storageKey: 'apikey_openrouter',
      },
      huggingface: {
        label: 'Hugging Face (huggingface.co/settings/tokens)',
        placeholder: 'hf_…',
        hint: 'Requiere token con permiso Inference Providers y un modelo disponible.',
        storageKey: 'apikey_hf',
      },
    };

    function $(id) { return document.getElementById(id); }

    function escHtml(s) {
      return String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    function setProvider(p) {
      if (isProcessing) return;
      currentProvider = p;
      const cfg = PROVIDERS[p];

      ['anthropic','openai','gemini','qwen','groq','kimi','deepseek','openrouter','huggingface'].forEach(k => {
        const btn = $(`btn-${k}`);
        if (!btn) return;
        if (k === p) {
          btn.className = 'provider-btn px-3.5 py-1.5 rounded-lg border text-sm font-medium transition-colors bg-indigo-600 border-indigo-600 text-white shadow-sm';
        } else {
          btn.className = 'provider-btn px-3.5 py-1.5 rounded-lg border text-sm font-medium transition-colors bg-white border-gray-300 text-gray-700 hover:border-indigo-400';
        }
      });

      $('keyLabel').textContent = cfg.label;
      $('apiKey').placeholder = cfg.placeholder;
      $('keyHint').textContent = cfg.hint;
      try { $('apiKey').value = sessionStorage.getItem(cfg.storageKey) || ''; localStorage.removeItem(cfg.storageKey); } catch (_) { $('apiKey').value = ''; }
      $('geminiModelWrap').classList.toggle('hidden', p !== 'gemini');
    }

    function saveKey(val) {
      try { sessionStorage.setItem(PROVIDERS[currentProvider].storageKey, val); } catch (_) {}
    }

    function setProgress(done, total) {
      const pct = total > 0 ? Math.round((done / total) * 100) : 0;
      $('progressBar').style.width = pct + '%';
      $('progressLabel').textContent = done < total
        ? `Procesando ${done} de ${total}…`
        : `✓ ${total} producto${total !== 1 ? 's' : ''} completado${total !== 1 ? 's' : ''}.`;
    }

    function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

    // Normalizador de medidas estrictamente al formato '45x34x10 cm' o '45x34 cm'
    function parseDimensions(text) {
      const part = '(\\d+(?:[.,]\\d+)?)\\s*(cm|mm|m)?';
      const match = String(text || '').match(new RegExp('(?<![\\d.,-])' + part + '\\s*[x×*]\\s*' + part + '(?:\\s*[x×*]\\s*' + part + ')?(?![\\d.,])', 'i'));
      if (!match) return '-';
      const pairs = [[match[1], match[2]], [match[3], match[4]], [match[5], match[6]]].filter(p => p[0]);
      const unit = [...pairs].reverse().find(p => p[1])?.[1]?.toLowerCase();
      if (!unit) return '-';
      const factors = {mm: 0.1, cm: 1, m: 100};
      const values = pairs.map(([n, u]) => Number(n.replace(',', '.')) * factors[u?.toLowerCase() || unit]);
      if (values.some(n => !Number.isFinite(n) || n <= 0)) return '-';
      return values.map(n => String(Number(n.toFixed(8)))).join('x') + ' cm';
    }

    // Catálogo de materiales para extracción verificada sin alucinaciones
    const KNOWN_MATERIALS = [
      { pattern: /\b(acero inoxidable|inox)\b/i, name: 'Acero inoxidable' },
      { pattern: /\b(acero al carbono|acero)\b/i, name: 'Acero' },
      { pattern: /\b(aluminio)\b/i, name: 'Aluminio' },
      { pattern: /\b(hierro fundido|hierro)\b/i, name: 'Hierro' },
      { pattern: /\b(lat[oó]n)\b/i, name: 'Latón' },
      { pattern: /\b(cobre)\b/i, name: 'Cobre' },
      { pattern: /\b(bronce)\b/i, name: 'Bronce' },
      { pattern: /\b(metal|met[aá]lico|met[aá]lica)\b/i, name: 'Metal' },
      { pattern: /\b(madera maciza|madera natural|madera)\b/i, name: 'Madera' },
      { pattern: /\b(bamb[uú])\b/i, name: 'Bambú' },
      { pattern: /\b(roble)\b/i, name: 'Roble' },
      { pattern: /\b(pino)\b/i, name: 'Pino' },
      { pattern: /\b(nogal)\b/i, name: 'Nogal' },
      { pattern: /\b(haya)\b/i, name: 'Haya' },
      { pattern: /\b(teca)\b/i, name: 'Teca' },
      { pattern: /\b(mdf|aglomerado|melamina)\b/i, name: 'MDF / Melamina' },
      { pattern: /\b(contrachapado)\b/i, name: 'Contrachapado' },
      { pattern: /\b(polipropileno|pp)\b/i, name: 'Polipropileno' },
      { pattern: /\b(polietileno|pe|hdpe)\b/i, name: 'Polietileno' },
      { pattern: /\b(policarbonato)\b/i, name: 'Policarbonato' },
      { pattern: /\b(acrilico|acr[ií]lico|metacrilato|plexigl[aá]s)\b/i, name: 'Acrílico' },
      { pattern: /\b(silicona)\b/i, name: 'Silicona' },
      { pattern: /\b(pvc|vinilo)\b/i, name: 'PVC' },
      { pattern: /\b(abs)\b/i, name: 'Plástico ABS' },
      { pattern: /\b(pl[aá]stico|plastic)\b/i, name: 'Plástico' },
      { pattern: /\b(resina)\b/i, name: 'Resina' },
      { pattern: /\b(goma|caucho)\b/i, name: 'Caucho' },
      { pattern: /\b(vidrio templado)\b/i, name: 'Vidrio templado' },
      { pattern: /\b(vidrio|cristal)\b/i, name: 'Vidrio' },
      { pattern: /\b(cer[aá]mica)\b/i, name: 'Cerámica' },
      { pattern: /\b(porcelana)\b/i, name: 'Porcelana' },
      { pattern: /\b(gres|barro|terracota)\b/i, name: 'Gres / Barro' },
      { pattern: /\b(algod[oó]n|cotton)\b/i, name: 'Algodón' },
      { pattern: /\b(lino|linen)\b/i, name: 'Lino' },
      { pattern: /\b(poli[eé]ster|polyester)\b/i, name: 'Poliéster' },
      { pattern: /\b(microfibra)\b/i, name: 'Microfibra' },
      { pattern: /\b(seda|silk)\b/i, name: 'Seda' },
      { pattern: /\b(lana|wool)\b/i, name: 'Lana' },
      { pattern: /\b(terciopelo)\b/i, name: 'Terciopelo' },
      { pattern: /\b(lona|canvas)\b/i, name: 'Lona' },
      { pattern: /\b(nylon|nailon)\b/i, name: 'Nylon' },
      { pattern: /\b(tela|tejido)\b/i, name: 'Textil' },
      { pattern: /\b(piel sint[eé]tica|polipiel|ecocuero|cuero sint[eé]tico)\b/i, name: 'Piel sintética' },
      { pattern: /\b(cuero aut[eé]ntico|cuero natural|cuero genuino|cuero)\b/i, name: 'Cuero' },
      { pattern: /\b(piel)\b/i, name: 'Piel' },
      { pattern: /\b(m[aá]rmol)\b/i, name: 'Mármol' },
      { pattern: /\b(granito)\b/i, name: 'Granito' },
      { pattern: /\b(pizarra)\b/i, name: 'Pizarra' },
      { pattern: /\b(piedra)\b/i, name: 'Piedra' },
      { pattern: /\b(corcho)\b/i, name: 'Corcho' },
      { pattern: /\b(rat[aá]n|mimbre)\b/i, name: 'Ratán / Mimbre' },
      { pattern: /\b(cart[oó]n)\b/i, name: 'Cartón' }
    ];

    function extractMaterialFromText(text) {
      if (!text) return '-';
      const str = String(text);
      for (const item of KNOWN_MATERIALS) {
        if (item.pattern.test(str)) {
          return item.name;
        }
      }
      return '-';
    }

    async function callAI(apiKey, imageUrl, name = '', dimensions = '', divisor = 1) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 230000);
      try {
      const resp = await fetch('/api/generate', {
        signal: controller.signal,
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: currentProvider,
          api_key: apiKey,
          image_url: imageUrl,
          name: name,
          dimensions: dimensions,
          divisor: divisor,
          model: currentProvider === 'gemini' ? ($('geminiModel').value.trim() || 'gemini-2.5-flash') : ''
        })
      });
      const data = await resp.json().catch(() => { throw new Error(`Respuesta no válida (HTTP ${resp.status})`); });
      if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
      if (!data.title) throw new Error('La IA devolvió una ficha vacía');
      return {
        title: data.title || '',
        highlights: data.highlights || '',
        material: data.material || '-',
        color: data.color || '-',
        medidas: data.medidas || '-',
        peso_g: data.peso_g ?? null,
        bullet_points: data.bullet_points || [],
        description: data.description || '',
        backend_keywords: data.backend_keywords || '',
        product_type: data.product_type || '',
        node_search_terms: data.node_search_terms || []
      };
      } finally { clearTimeout(timeout); }
    }

    function parseDivisor(val) {
      if (val === null || val === undefined || val === '') return 1;
      const str = String(val).trim().toLowerCase().replace(/^x\s*/i, '');
      const n = parseInt(str, 10);
      return (!isNaN(n) && n > 0) ? n : 1;
    }

    function isNumericOrMultiplier(val) {
      if (val === null || val === undefined || val === '') return false;
      const s = String(val).trim().toLowerCase();
      return /^x?\d+$/i.test(s);
    }

    let imagePreviewLoad = 0;

    function clearImagePreview() {
      imagePreviewLoad++;
      $('imagePreviewList').replaceChildren();
      $('imagePreviewPanel').classList.add('hidden');
      $('imagePreviewStatus').textContent = '';
      $('imagePreviewInput').value = '';
    }

    async function loadImagePreview(input) {
      const file = input.files[0];
      if (!file) return;
      const load = ++imagePreviewLoad;
      const status = $('imagePreviewStatus');
      status.textContent = 'Leyendo listado…';
      try {
        if (file.size > 10 * 1024 * 1024) throw new Error('El archivo supera 10 MB.');
        if (typeof XLSX === 'undefined') throw new Error('No se pudo cargar el lector Excel. Recarga la página.');
        const data = await file.arrayBuffer();
        if (load !== imagePreviewLoad) return;
        const workbook = XLSX.read(data, { type: 'array' });
        const first = workbook.Sheets[workbook.SheetNames[0]];
        if (!first) throw new Error('El archivo no contiene hojas.');
        // Formatted strings preserve displayed product references such as 000123.
        const rows = XLSX.utils.sheet_to_json(first, { header: 1, raw: false, defval: '' })
          .filter(row => String(row[0] ?? '').trim() || String(row[1] ?? '').trim() || String(row[2] ?? '').trim());
        const header = String(rows[0]?.[1] ?? '').trim();
        if (/^(url(?:[ _-]+(?:de[ _-]+(?:la[ _-]+)?)?(?:imagen|image))?|image[ _-]+url|enlace(?: de imagen)?)$/i.test(header)) rows.shift();
        if (!rows.length) throw new Error('No hay productos. Usa la columna A para el número y la B para la URL.');
        if (rows.length > 1000) throw new Error('El listado supera 1000 productos. Divide el archivo en varios lotes.');
        const fragment = document.createDocumentFragment();
        let invalid = 0;
        for (const row of rows) {
          let ref = String(row[0] ?? '').trim();
          let url = String(row[1] ?? '').trim();
          let divisor = 1;
          if (isNumericOrMultiplier(row[1]) && row[2] && isImageURL(String(row[2]).trim())) {
            divisor = parseDivisor(row[1]);
            url = String(row[2]).trim();
          }
          const item = document.createElement('li');
          item.className = 'flex items-center gap-4 py-3';
          const label = document.createElement('span');
          label.className = 'font-semibold text-gray-800 break-words';
          label.style.cssText = 'width: min(40%, 12rem); flex-shrink: 0; overflow-wrap: anywhere';
          label.textContent = (ref || 'Sin número de producto') + (divisor > 1 ? ` (x${divisor})` : '');
          item.append(label);
          const box = document.createElement('div');
          box.style.cssText = 'width: 144px; min-height: 144px; max-width: 55%';
          item.append(box);
          let valid = false;
          try {
            const parsed = new URL(url);
            valid = ['http:', 'https:'].includes(parsed.protocol) && !parsed.username && !parsed.password;
          } catch (_) { /* Show invalid rows so no reference silently disappears. */ }
          const note = document.createElement('span');
          note.className = 'text-sm text-gray-500';
          if (!valid) {
            invalid++;
            note.textContent = 'URL de imagen vacía o no válida';
          } else {
            const img = document.createElement('img');
            img.alt = `Producto ${ref || 'sin referencia'}`;
            img.loading = 'lazy';
            img.decoding = 'async';
            img.referrerPolicy = 'no-referrer';
            img.width = 144;
            img.height = 144;
            img.style.cssText = 'width: 100%; height: 144px; object-fit: contain';
            note.textContent = 'Cargando imagen…';
            img.onload = () => { note.textContent = ''; };
            img.onerror = () => { img.hidden = true; note.textContent = 'No se pudo cargar la imagen'; };
            img.src = url;
            box.append(img);
          }
          box.append(note);
          fragment.append(item);
        }
        $('imagePreviewList').replaceChildren(fragment);
        $('imagePreviewPanel').classList.remove('hidden');
        status.textContent = `${file.name}: ${rows.length} productos${invalid ? ` · ${invalid} URL no válidas` : ''}.`;
      } catch (error) {
        if (load === imagePreviewLoad) status.textContent = `No se pudo cargar el nuevo listado: ${error.message}`;
      } finally {
        if (load === imagePreviewLoad) input.value = '';
      }
    }

    function handleFile(input) {
      if (isProcessing) return;
      window.pendingData = null;
      const file = input.files[0];
      if (!file) return;
      if (file.size > 10 * 1024 * 1024) { alert('El archivo supera 10 MB'); return; }
      if (typeof XLSX === 'undefined') { alert('No se pudo cargar el lector Excel. Recarga la página.'); return; }
      const reader = new FileReader();
      reader.onload = (e) => {
        if (isProcessing) return;
        try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 });
        if (!rows || !rows.length) { alert('El archivo está vacío.'); return; }

        let startIdx = 0;
        const firstRow = rows[0] || [];
        const isHeaderRow = firstRow.some(c => {
          const s = String(c ?? '').toLowerCase();
          return ['url', 'enlace', 'imagen', 'image', 'divisor', 'unidades', 'cant', 'pack', 'nombre', 'medidas'].some(k => s.includes(k));
        });
        if (isHeaderRow) {
          startIdx = 1;
        }

        let urls = [];
        for (let r = startIdx; r < rows.length; r++) {
          const row = rows[r];
          if (!row || !row.length) continue;

          let url = '';
          let divisor = 1;
          let name = '';
          let rawDims = '';
          let ref = '';

          // Caso 1: Columna A (row[0]) es URL de imagen
          if (row[0] && isImageURL(String(row[0]).trim())) {
            url = String(row[0]).trim();
            if (isNumericOrMultiplier(row[1])) {
              divisor = parseDivisor(row[1]);
              name = row[2] ? String(row[2]).trim() : '';
              rawDims = row[3] ? String(row[3]).trim() : '';
            } else {
              divisor = 1;
              name = row[1] ? String(row[1]).trim() : '';
              rawDims = row[2] ? String(row[2]).trim() : '';
            }
          }
          // Caso 2: Columna A es SKU/Ref, Columna B es Divisor, Columna C es URL
          else if (row[2] && isImageURL(String(row[2]).trim())) {
            ref = String(row[0] ?? '').trim();
            divisor = parseDivisor(row[1]);
            url = String(row[2]).trim();
            name = row[3] ? String(row[3]).trim() : '';
            rawDims = row[4] ? String(row[4]).trim() : '';
          }
          // Caso 3: Columna A es SKU/Ref, Columna B es URL (ej: IMAGENES.xlsx)
          else if (row[1] && isImageURL(String(row[1]).trim())) {
            ref = String(row[0] ?? '').trim();
            url = String(row[1]).trim();
            if (isNumericOrMultiplier(row[2])) {
              divisor = parseDivisor(row[2]);
              name = row[3] ? String(row[3]).trim() : '';
              rawDims = row[4] ? String(row[4]).trim() : '';
            } else {
              divisor = 1;
              name = row[2] ? String(row[2]).trim() : '';
              rawDims = row[3] ? String(row[3]).trim() : '';
            }
          }

          if (url && isImageURL(url)) {
            const extractedDims = parseDimensions(rawDims) !== '-' ? parseDimensions(rawDims) : parseDimensions(name);
            const extractedMaterial = extractMaterialFromText(name) !== '-' ? extractMaterialFromText(name) : extractMaterialFromText(rawDims);

            urls.push({
              url: url,
              ref: ref || getRef(url),
              divisor: divisor,
              name: name,
              rawDims: rawDims,
              dims: extractedDims,
              material: extractedMaterial
            });
          }
        }
        
        if (urls.length > 0) {
          window.pendingData = urls;
          $('progressLabel').textContent = `✓ ${urls.length} filas cargadas desde el archivo. Pulsa "Procesar imágenes".`;
        } else {
          alert('No se encontraron URLs válidas en el archivo.');
        }
        } catch (error) { alert('No se pudo importar el archivo: ' + error.message); }
      };
      reader.onerror = () => alert('No se pudo leer el archivo');
      reader.readAsArrayBuffer(file);
    }

    function isImageURL(value) {
      try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password; }
      catch (_) { return false; }
    }

    function getRef(url) {
      try { return decodeURIComponent(new URL(url).pathname.split('/').pop()).replace(/\.[^/.]+$/, '') || '-'; }
      catch (_) { return '-'; }
    }

    function addRow(index, item) {
      const tbody = $('resultsBody');
      const tr = document.createElement('tr');
      tr.id = `row-${index}`;
      tr.className = 'fade-in hover:bg-gray-50/70 transition-colors';
      const ph = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='50' height='50'%3E%3Crect width='50' height='50' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%239ca3af' font-size='9' font-family='sans-serif'%3EN/A%3C/text%3E%3C/svg%3E`;

      tr.innerHTML = `
        <td class="px-3 py-3 align-top">
          <a href="${escHtml(item.url)}" target="_blank" rel="noopener noreferrer" title="Ver imagen original">
            <img src="${escHtml(item.url)}" width="48" height="48"
              class="w-12 h-12 object-cover rounded-md border border-gray-200 bg-gray-100 hover:scale-105 transition-transform"
              loading="lazy">
          </a>
        </td>
        <td class="px-3 py-3 align-top text-xs font-mono font-semibold text-gray-600">
          ${escHtml(item.ref || getRef(item.url))}
        </td>
        <td class="px-3 py-3 align-top text-xs text-gray-500">
          <div class="font-semibold text-gray-800 line-clamp-2">
            ${item.divisor && item.divisor > 1 ? `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 mr-1" title="Pack de ${item.divisor} unidades">x${item.divisor}</span>` : ''}${escHtml(item.name || '-')}
          </div>
          <div class="text-gray-400 mt-0.5">${escHtml(item.rawDims || item.dims || '-')}</div>
        </td>
        <td class="px-3 py-3 align-top" id="cell-title-${index}">
          <span class="text-gray-400 text-xs"><span class="spinner"></span>Generando título…</span>
        </td>
        <td class="px-3 py-3 align-top" id="cell-highlights-${index}">
          <span class="text-gray-400 text-xs"><span class="spinner"></span>Generando highlights…</span>
        </td>
        <td class="px-3 py-3 align-top" id="cell-material-${index}">
          <span class="text-gray-400 text-xs">${item.material && item.material !== '-' ? escHtml(item.material) : '<span class="spinner"></span>Analizando…'}</span>
        </td>
        <td class="px-3 py-3 align-top font-medium text-xs" id="cell-color-${index}">
          <span class="text-gray-400 text-xs">${item.color && item.color !== '-' ? escHtml(item.color) : '<span class="spinner"></span>Detectando…'}</span>
        </td>
        <td class="px-3 py-3 align-top font-mono text-xs" id="cell-medidas-${index}">
          <span class="text-gray-400 text-xs">${item.dims && item.dims !== '-' ? escHtml(item.dims) : '<span class="spinner"></span>Analizando…'}</span>
        </td>
        <td class="px-3 py-3 align-top" id="cell-peso-${index}">—</td>
        <td class="px-3 py-3 align-top" id="cell-bullets-${index}">
          <span class="text-gray-400 text-xs"><span class="spinner"></span>Generando bullets…</span>
        </td>
        <td class="px-3 py-3 align-top" id="cell-description-${index}">
          <span class="text-gray-400 text-xs"><span class="spinner"></span>Generando descripción…</span>
        </td>
        <td class="px-3 py-3 align-top" id="cell-keywords-${index}">
          <span class="text-gray-400 text-xs"><span class="spinner"></span>Generando keywords…</span>
        </td>
        <td class="px-3 py-3 align-top min-w-[280px]" id="cell-node-${index}">
          <span class="text-gray-400 text-xs">Pendiente del título</span>
        </td>
        <td class="px-3 py-3 align-top text-center" id="cell-actions-${index}">
          <span class="text-gray-300 text-xs">-</span>
        </td>`;
      tr.querySelector("img").addEventListener("error", event => { event.currentTarget.src = ph; }, {once: true});
      tbody.appendChild(tr);
    }

    function updateCounters(index) {
      const titleElem = $(`title-text-${index}`);
      const highElem = $(`highlights-text-${index}`);
      if (!titleElem || !highElem) return;

      const titleText = titleElem.innerText.trim();
      const highText = highElem.innerText.trim();

      // Guardar en results
      if (results[index]) {
        if (results[index].title !== titleText || results[index].highlights !== highText) invalidateNode(index);
        results[index].title = titleText;
        results[index].highlights = highText;
      }

      // Contador Título (máx 75)
      const tLen = titleText.length;
      const tCounter = $(`title-count-${index}`);
      if (tCounter) {
        tCounter.textContent = `${tLen}/75 car.`;
        if (tLen > 75) {
          tCounter.className = 'text-[10px] font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded';
        } else if (tLen >= 40) {
          tCounter.className = 'text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded';
        } else {
          tCounter.className = 'text-[10px] font-semibold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded';
        }
      }

      // Contador Highlights (máx 125)
      const hLen = highText.length;
      const hCounter = $(`highlights-count-${index}`);
      if (hCounter) {
        hCounter.textContent = `${hLen}/125 car.`;
        if (hLen > 125) {
          hCounter.className = 'text-[10px] font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded';
        } else if (hLen >= 50) {
          hCounter.className = 'text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded';
        } else {
          hCounter.className = 'text-[10px] font-semibold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded';
        }
      }

      // Contador Backend Keywords (máx 250)
      const keyElem = $(`keywords-text-${index}`);
      if (keyElem && results[index]) {
        const keyText = keyElem.innerText.trim();
        if (results[index].backend_keywords !== keyText) invalidateNode(index);
        results[index].backend_keywords = keyText;
        const kLen = keyText.length;
        const kCounter = $(`keywords-count-${index}`);
        if (kCounter) {
          kCounter.textContent = `${kLen}/250 car.`;
          if (kLen > 250) {
            kCounter.className = 'text-[10px] font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded';
          } else if (kLen >= 100) {
            kCounter.className = 'text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded';
          } else {
            kCounter.className = 'text-[10px] font-semibold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded';
          }
        }
      }
    }

    function updateMaterial(index) {
      const el = $(`material-text-${index}`);
      if (el && results[index]) {
        if (results[index].material !== (el.innerText.trim() || '-')) invalidateNode(index);
        results[index].material = el.innerText.trim() || '-';
      }
    }

    function updateColor(index) {
      const el = $(`color-text-${index}`);
      if (el && results[index]) {
        if (results[index].color !== (el.innerText.trim() || '-')) invalidateNode(index);
        results[index].color = el.innerText.trim() || '-';
      }
    }

    function updateMedidas(index) {
      const el = $(`medidas-text-${index}`);
      if (el && results[index]) {
        if (results[index].medidas !== (el.innerText.trim() || '-')) invalidateNode(index);
        results[index].medidas = el.innerText.trim() || '-';
      }
    }

    function updateListingFields(index) {
      if (!results[index]) return;
      invalidateNode(index);
      const descEl = $(`description-${index}`);
      if (descEl) results[index].description = descEl.innerText.trim();
      const bullets = [];
      for (let i = 0; i < 5; i++) {
        const b = $(`bullet-${index}-${i}`);
        if (b) bullets.push(b.innerText.trim());
      }
      if (bullets.length) results[index].bullet_points = bullets;
    }

    function updateProductWeight(index, input) {
      const value = input.value.trim();
      const number = Number(value);
      const valid = !value || (Number.isFinite(number) && number > 0);
      input.setCustomValidity(valid ? '' : 'Introduce un peso positivo en gramos');
      results[index].peso_g = value ? (valid ? number : value) : null;
    }

    function setRowSuccess(index, title, highlights, material, color = '-', medidas = '-', bulletPoints = [], description = '', backendKeywords = '') {
      const cellTitle = $(`cell-title-${index}`);
      const cellHigh = $(`cell-highlights-${index}`);
      const cellMat = $(`cell-material-${index}`);
      const cellColor = $(`cell-color-${index}`);
      const cellMed = $(`cell-medidas-${index}`);
      const cellBullets = $(`cell-bullets-${index}`);
      const cellDesc = $(`cell-description-${index}`);
      const cellKeywords = $(`cell-keywords-${index}`);
      const cellActions = $(`cell-actions-${index}`);
      if (!cellTitle || !cellHigh) return;

      renderNode(index);
      const tLen = title.length;
      const hLen = highlights.length;

      cellTitle.innerHTML = `
        <div class="flex flex-col gap-1">
          <div id="title-text-${index}" contenteditable="true" spellcheck="false"
            oninput="updateCounters(${index})"
            class="editable-cell text-gray-900 font-medium text-xs leading-snug p-2 rounded border border-transparent hover:border-gray-200">
            ${escHtml(title)}
          </div>
          <div class="flex items-center justify-between px-1">
            <span id="title-count-${index}" class="${tLen > 75 ? 'text-[10px] font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded' : 'text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded'}">
              ${tLen}/75 car.
            </span>
            <button onclick="copyField(${index}, 'title')" class="text-[11px] text-gray-400 hover:text-indigo-600 flex items-center gap-1 transition-colors">
              Copiar
            </button>
          </div>
        </div>`;

      cellHigh.innerHTML = `
        <div class="flex flex-col gap-1">
          <div id="highlights-text-${index}" contenteditable="true" spellcheck="false"
            oninput="updateCounters(${index})"
            class="editable-cell text-gray-800 text-xs leading-snug p-2 rounded border border-transparent hover:border-gray-200">
            ${escHtml(highlights)}
          </div>
          <div class="flex items-center justify-between px-1">
            <span id="highlights-count-${index}" class="${hLen > 125 ? 'text-[10px] font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded' : 'text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded'}">
              ${hLen}/125 car.
            </span>
            <button onclick="copyField(${index}, 'highlights')" class="text-[11px] text-gray-400 hover:text-indigo-600 flex items-center gap-1 transition-colors">
              Copiar
            </button>
          </div>
        </div>`;

      if (cellMat) {
        cellMat.innerHTML = `
          <div id="material-text-${index}" contenteditable="true" spellcheck="false"
            oninput="updateMaterial(${index})"
            class="editable-cell text-xs font-medium ${material !== '-' ? 'text-emerald-800 bg-emerald-50/70' : 'text-gray-400'} px-2 py-1 rounded border border-transparent hover:border-gray-200">
            ${escHtml(material)}
          </div>`;
      }

      if (cellColor) {
        cellColor.innerHTML = `
          <div id="color-text-${index}" contenteditable="true" spellcheck="false"
            oninput="updateColor(${index})"
            class="editable-cell text-xs font-medium ${color !== '-' ? 'text-amber-800 bg-amber-50/70' : 'text-gray-400'} px-2 py-1 rounded border border-transparent hover:border-gray-200">
            ${escHtml(color)}
          </div>`;
      }

      if (cellMed) {
        cellMed.innerHTML = `
          <div id="medidas-text-${index}" contenteditable="true" spellcheck="false"
            oninput="updateMedidas(${index})"
            class="editable-cell font-mono text-xs ${medidas !== '-' ? 'text-indigo-900 bg-indigo-50/70 font-semibold' : 'text-gray-400'} px-2 py-1 rounded border border-transparent hover:border-gray-200">
            ${escHtml(medidas)}
          </div>`;
      }

      const weightCell = $(`cell-peso-${index}`);
      if (weightCell) {
        weightCell.innerHTML = `<input type="number" min="0.001" step="any" aria-label="Peso del producto en gramos" placeholder="Sin dato" class="border rounded px-2 py-1 w-28" value="${escHtml(String(results[index]?.peso_g ?? ''))}" oninput="updateProductWeight(${index}, this)"><span class="text-xs ml-1">g</span>`;
      }
      if (cellBullets) {
        const bulletsList = Array.from({length: 5}, (_, i) => bulletPoints[i] || '');
        cellBullets.innerHTML = `
          <div class="flex flex-col gap-1">
            <ol class="list-decimal pl-4 space-y-1 text-xs text-gray-800">
              ${bulletsList.map((b, bi) => `
                <li id="bullet-${index}-${bi}" contenteditable="true" spellcheck="false"
                  oninput="updateListingFields(${index})"
                  class="editable-cell p-1 rounded hover:border-gray-200 border border-transparent">
                  ${escHtml(b)}
                </li>
              `).join('')}
            </ol>
            <div class="flex justify-end pt-1">
              <button onclick="copyField(${index}, 'bullets')" class="text-[11px] text-gray-400 hover:text-indigo-600 flex items-center gap-1 transition-colors">
                Copiar bullets
              </button>
            </div>
          </div>`;
      }

      if (cellDesc) {
        cellDesc.innerHTML = `
          <div class="flex flex-col gap-1">
            <div id="description-${index}" contenteditable="true" spellcheck="false"
              oninput="updateListingFields(${index})"
              class="editable-cell text-xs leading-snug p-2 rounded border border-transparent hover:border-gray-200 text-gray-800 max-h-36 overflow-y-auto">
              ${escHtml(description)}
            </div>
            <div class="flex justify-end">
              <button onclick="copyField(${index}, 'description')" class="text-[11px] text-gray-400 hover:text-indigo-600 flex items-center gap-1 transition-colors">
                Copiar desc.
              </button>
            </div>
          </div>`;
      }

      if (cellKeywords) {
        const kLen = (backendKeywords || '').length;
        cellKeywords.innerHTML = `
          <div class="flex flex-col gap-1">
            <div id="keywords-text-${index}" contenteditable="true" spellcheck="false"
              oninput="updateCounters(${index})"
              class="editable-cell text-xs leading-snug p-2 rounded border border-transparent hover:border-gray-200 text-gray-800 max-h-36 overflow-y-auto">
              ${escHtml(backendKeywords || '')}
            </div>
            <div class="flex items-center justify-between px-1">
              <span id="keywords-count-${index}" class="${kLen > 250 ? 'text-[10px] font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded' : 'text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded'}">
                ${kLen}/250 car.
              </span>
              <button onclick="copyField(${index}, 'keywords')" class="text-[11px] text-gray-400 hover:text-indigo-600 flex items-center gap-1 transition-colors">
                Copiar keywords
              </button>
            </div>
          </div>`;
      }

      if (cellActions) {
        cellActions.innerHTML = `
          <button onclick="copyBoth(${index})" title="Copiar Ficha Completa"
            class="px-2.5 py-1 text-xs font-semibold bg-gray-100 hover:bg-indigo-50 hover:text-indigo-600 text-gray-700 rounded transition-colors border border-gray-200">
            Copiar todo
          </button>`;
      }
    }

    function setRowError(index, errorMsg, material = '-', color = '-', medidas = '-') {
      const cellTitle = $(`cell-title-${index}`);
      const cellHigh = $(`cell-highlights-${index}`);
      const cellMat = $(`cell-material-${index}`);
      const cellColor = $(`cell-color-${index}`);
      const cellMed = $(`cell-medidas-${index}`);
      const cellBullets = $(`cell-bullets-${index}`);
      const cellDesc = $(`cell-description-${index}`);
      const cellKeywords = $(`cell-keywords-${index}`);
      renderNode(index);
      if (cellTitle) cellTitle.innerHTML = `<span class="text-red-500 text-xs font-medium">${escHtml(errorMsg)}</span>`;
      if (cellHigh) cellHigh.innerHTML = `<span class="text-gray-400 text-xs">No generado</span>`;
      if (cellMat) cellMat.innerHTML = `<span class="text-gray-400 text-xs">${escHtml(material)}</span>`;
      if (cellColor) cellColor.innerHTML = `<span class="text-gray-400 text-xs">${escHtml(color)}</span>`;
      if (cellMed) cellMed.innerHTML = `<span class="text-gray-400 text-xs">${escHtml(medidas)}</span>`;
      if (cellBullets) cellBullets.innerHTML = `<span class="text-gray-400 text-xs">No generado</span>`;
      if (cellDesc) cellDesc.innerHTML = `<span class="text-gray-400 text-xs">No generado</span>`;
      if (cellKeywords) cellKeywords.innerHTML = `<span class="text-gray-400 text-xs">No generado</span>`;
    }

    function copyField(index, field) {
      const item = results[index];
      if (!item) return;
      let text = '';
      if (field === 'bullets') {
        text = (item.bullet_points || []).map((b, i) => `${i + 1}. ${b}`).join('\n');
      } else if (field === 'description') {
        text = item.description || '';
      } else if (field === 'keywords') {
        text = item.backend_keywords || '';
      } else {
        text = item[field] || '';
      }
      if (!text) return;
      navigator.clipboard.writeText(text).then(() => {
        showToast(`Copiado: ${field}`);
      }).catch(() => alert('No se pudo copiar. Comprueba los permisos del portapapeles.'));
    }

    function copyBoth(index) {
      const item = results[index];
      if (!item) return;
      const bulletsText = (item.bullet_points || []).map((b, i) => `• ${b}`).join('\n');
      const text = `Título:\n${item.title}\n\nHighlights:\n${item.highlights}\n\nMaterial:\n${item.material || '-'}\n\nColor:\n${item.color || '-'}\n\nMedidas:\n${item.medidas || '-'}\n\nPeso del producto (g):\n${item.peso_g ?? 'Sin dato'}\n\nBullet Points:\n${bulletsText}\n\nDescripción:\n${item.description || ''}\n\nBackend Keywords:\n${item.backend_keywords || ''}\n\nNodo Amazon.es:\n${item.node_id || 'Pendiente'}\n${item.node_path || ''}\nEstado: ${item.node_status || 'pendiente'}`;
      navigator.clipboard.writeText(text).then(() => {
        showToast(`Ficha completa copiada al portapapeles`);
      }).catch(() => alert('No se pudo copiar. Comprueba los permisos del portapapeles.'));
    }

    function showToast(msg) {
      let toast = $('app-toast');
      if (!toast) {
        toast = document.createElement('div');
        toast.id = 'app-toast';
        toast.className = 'fixed bottom-5 right-5 bg-gray-900 text-white text-xs font-medium px-3.5 py-2 rounded-lg shadow-lg z-50 transition-opacity duration-300 pointer-events-none opacity-0';
        document.body.appendChild(toast);
      }
      toast.textContent = msg;
      toast.classList.remove('opacity-0');
      toast.classList.add('opacity-100');
      setTimeout(() => {
        toast.classList.remove('opacity-100');
        toast.classList.add('opacity-0');
      }, 2000);
    }

    async function processImages(retryFailed = false) {
      if (isProcessing) return;
      const apiKey = $('apiKey').value.trim();

      let items = [];
      if (retryFailed) {
        items = results.map(r => ({...r, color: r.color || '-', dims: r.medidas || '-', rawDims: r.rawDims || '', divisor: r.divisor || 1}));
        if (!items.some(r => r.error)) return;
      } else if (window.pendingData && window.pendingData.length > 0) {
        items = window.pendingData;
      } else {
        const urls = $('urlsInput').value.trim().split('\n').map(u => u.trim()).filter(Boolean);
        items = urls.map(u => ({ url: u, divisor: 1, name: '', rawDims: '', dims: '-', material: '-', color: '-' }));
      }
      
      if (items.length === 0) { alert('Introduce al menos una URL o carga un archivo Excel.'); return; }

      if (items.some(item => !isImageURL(item.url))) { alert('Todas las imágenes deben ser URLs HTTP(S) válidas'); return; }
      if (items.length > 1000) { alert('El máximo es 1000 productos por lote'); return; }
      isProcessing = true;
      const locked = [...document.querySelectorAll('input, textarea, select, .supplier-tab, .provider-btn')].map(el => [el, el.disabled]);
      locked.forEach(([el]) => el.disabled = true);
      if (!retryFailed) results = [];
      $('resultsBody').innerHTML = '';
      $('resultsContainer').classList.remove('hidden');
      $('exportGroup').classList.add('hidden');
      $('progressBarWrap').classList.remove('hidden');
      $('progressBar').style.width = '0%';
      $('resultsCount').textContent = items.length;
      setProgress(0, items.length);

      const btn = $('processBtn');
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner"></span> Procesando…`;
      btn.classList.add('opacity-60', 'cursor-not-allowed');

      try {
      items.forEach((item, i) => {
        addRow(i, item);
        if (retryFailed && !item.error) setRowSuccess(i, item.title, item.highlights, item.material, item.color, item.medidas, item.bullet_points, item.description, item.backend_keywords);
      });

      for (let i = 0; i < items.length; i++) {
        if (retryFailed && !items[i].error) continue;
        try {
          if (['gemini', 'groq'].includes(currentProvider) && i > 0) {
            const waitTime = currentProvider === 'gemini' ? 8000 : 4000;
            await sleep(waitTime);
          }
          const promptDims = items[i].rawDims || (items[i].dims !== '-' ? items[i].dims : '');
          const out = await callAI(apiKey, items[i].url, items[i].name, promptDims, items[i].divisor || 1);
          
          // Extracción de material (cero alucinaciones)
          let finalMaterial = '-';
          if (items[i].material && items[i].material !== '-') {
            finalMaterial = items[i].material;
          } else if (out.material && out.material !== '-') {
            finalMaterial = out.material;
          }

          // Extracción de color predominante / multicolor
          let finalColor = '-';
          if (out.color && out.color !== '-') {
            finalColor = out.color;
          } else if (items[i].color && items[i].color !== '-') {
            finalColor = items[i].color;
          }

          // Extracción de medidas en formato estandarizado
          let finalMedidas = '-';
          if (items[i].dims && items[i].dims !== '-') {
            finalMedidas = items[i].dims;
          } else if (out.medidas && out.medidas !== '-') {
            finalMedidas = out.medidas;
          }

          results[i] = {
            url: items[i].url,
            ref: items[i].ref || getRef(items[i].url),
            divisor: items[i].divisor || 1,
            name: items[i].name,
            rawDims: items[i].rawDims || items[i].dims,
            title: out.title,
            highlights: out.highlights,
            material: finalMaterial,
            color: finalColor,
            medidas: finalMedidas,
            peso_g: out.peso_g ?? null,
            bullet_points: out.bullet_points || [],
            description: out.description || '',
            backend_keywords: out.backend_keywords || '',
            product_type: out.product_type || '',
            node_search_terms: out.node_search_terms || []
          };
          setRowSuccess(i, out.title, out.highlights, finalMaterial, finalColor, finalMedidas, out.bullet_points, out.description, out.backend_keywords);
          await assignNode(i, apiKey);
        } catch (e) {
          const fallbackMat = items[i].material || '-';
          const fallbackColor = items[i].color || '-';
          const fallbackMed = items[i].dims || '-';
          results[i] = {
            url: items[i].url,
            ref: items[i].ref || getRef(items[i].url),
            divisor: items[i].divisor || 1,
            name: items[i].name,
            rawDims: items[i].rawDims || items[i].dims,
            title: '',
            error: e.message,
            highlights: '',
            material: fallbackMat,
            color: fallbackColor,
            medidas: fallbackMed,
            peso_g: null,
            bullet_points: [],
            description: '',
            backend_keywords: '',
            product_type: '',
            node_search_terms: []
          };
          setRowError(i, `Error: ${e.message}`, fallbackMat, fallbackColor, fallbackMed);
        }
        setProgress(i + 1, items.length);
      }

      } finally {
      isProcessing = false;
      results.forEach((_, i) => renderNode(i));
      locked.forEach(([el, disabled]) => el.disabled = disabled);
      btn.disabled = false;
      btn.innerHTML = `<span>⚡ Procesar imágenes</span>`;
      btn.classList.remove('opacity-60', 'cursor-not-allowed');
      $('exportGroup').classList.remove('hidden');
      window.pendingData = null;
      supplierState[activeSupplier].results = results;
      supplierState[activeSupplier].pendingData = null;
      updateSupplierCounts();
      updateResultsSummary();
      }
    }

    // Generar fichero oficial de importación masiva de Amazon (.xlsm) para Signes
    async function generateBulkImport() {
      const validResults = results.filter(r => !r.error);
      if (!validResults.length) {
        alert('Primero genera o introduce fichas de producto antes de generar el fichero de importación masiva.');
        return;
      }

      const btn = $('bulkImportBtn');
      const originalText = btn ? btn.innerHTML : '';
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-1.5"></span>Generando Excel…`;
      }

      try {
        const items = validResults.map(r => ({
          ref: r.ref || getRef(r.url),
          divisor: r.divisor || 1,
          url: r.url || '',
          image_url: r.url || '',
          title: r.title || '',
          highlights: r.highlights || '',
          node_id: r.node_id || '',
          description: r.description || '',
          bullet_points: r.bullet_points || [],
          material: r.material || '',
          color: r.color || '',
          medidas: r.medidas || '',
          peso_g: r.peso_g ?? null,
          backend_keywords: r.backend_keywords || ''
        }));

        const resp = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'export_bulk',
            supplier: activeSupplier,
            items: items
          })
        });

        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.error || 'Error al generar la plantilla de importación');
        }

        const byteCharacters = atob(data.content_b64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: data.mime || 'application/vnd.ms-excel.sheet.macroEnabled.12' });

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename || `Amazon_Bulk_Import_Signes_${new Date().toISOString().slice(0, 10)}.xlsm`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast(`Fichero de importación generado (${items.length} productos)`);
      } catch (err) {
        alert(`❌ Error al generar fichero de importación: ${err.message}`);
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = originalText;
        }
      }
    }

    // Exportación a Excel (.xlsx) completa
    function exportExcel() {
      if (!results.length) return;
      if (typeof XLSX === 'undefined') { alert('No se pudo cargar Excel. Puedes descargar CSV.'); return; }
      const data = [
        [
          "Referencia",
          "Título Amazon (≤ 75 car.)",
          "Item Highlights (≤ 125 car.)",
          "Material",
          "Color",
          "Medidas",
          "Peso del producto (g)",
          "Bullet 1",
          "Bullet 2",
          "Bullet 3",
          "Bullet 4",
          "Bullet 5",
          "Descripción",
          "Backend Keywords",
          "Longitud Título",
          "Longitud Highlights",
          "Longitud Keywords",
          "URL Imagen",
          "Contexto / Datos Originales",
          "Nodo Amazon.es (columna B)", "Categoría Amazon", "Estado nodo", "Confianza nodo", "Motivo nodo"
        ]
      ];

      results.filter(r => !r.error).forEach(r => {
        const bp = r.bullet_points || [];
        data.push([
          r.ref || getRef(r.url),
          r.title || '',
          r.highlights || '',
          r.material || '-',
          r.color || '-',
          r.medidas || '-',
          r.peso_g ?? '',
          bp[0] || '',
          bp[1] || '',
          bp[2] || '',
          bp[3] || '',
          bp[4] || '',
          r.description || '',
          r.backend_keywords || '',
          (r.title || '').length,
          (r.highlights || '').length,
          (r.backend_keywords || '').length,
          r.url || '',
          [r.name, r.rawDims].filter(Boolean).join(' | '),
          ...nodeExportValues(r)
        ]);
      });

      const ws = XLSX.utils.aoa_to_sheet(data);
      ws['!cols'] = [
        { wch: 16 }, // Ref
        { wch: 45 }, // Titulo
        { wch: 55 }, // Highlights
        { wch: 20 }, // Material
        { wch: 18 }, // Color
        { wch: 18 }, // Medidas
        { wch: 22 }, // Peso del producto (g)
        { wch: 35 }, { wch: 35 }, { wch: 35 }, { wch: 35 }, { wch: 35 }, // Bullets 1-5
        { wch: 50 }, // Descripcion
        { wch: 45 }, // Backend Keywords
        { wch: 15 }, // Car Titulo
        { wch: 18 }, // Car Highlights
        { wch: 18 }, // Car Keywords
        { wch: 35 }, // URL
        { wch: 30 }, // Contexto
        { wch: 20 }, { wch: 70 }, { wch: 18 }, { wch: 18 }, { wch: 65 }
      ];

      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Listings Amazon");
      const filename = `amazon_listings_2026_${new Date().toISOString().slice(0,10)}.xlsx`;
      XLSX.writeFile(wb, filename);
      showToast("Excel descargado correctamente");
    }

    // Descarga directa CSV en el navegador
    function exportCSVLocal() {
      if (!results.length) return;
      const rows = results.filter(r => !r.error).map(r => {
        const bp = r.bullet_points || [];
        return [
          r.ref || getRef(r.url),
          r.title || '',
          r.highlights || '',
          r.material || '-',
          r.color || '-',
          r.medidas || '-',
          r.peso_g ?? '',
          bp[0] || '',
          bp[1] || '',
          bp[2] || '',
          bp[3] || '',
          bp[4] || '',
          r.description || '',
          r.backend_keywords || '',
          ...nodeExportValues(r)
        ].map(val => `"${safeCell(val).replace(/"/g, '""')}"`).join(',');
      });
      const csvContent = '\uFEFFreferencia,titulo,highlights,material,color,medidas,peso_producto_g,bullet_1,bullet_2,bullet_3,bullet_4,bullet_5,descripcion,backend_keywords,nodo_amazon_es,categoria_amazon,estado_nodo,confianza_nodo,motivo_nodo\n' + rows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `titulos_highlights_amazon_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast("CSV descargado en el navegador");
    }

    // Guardar en la carpeta ~/Downloads mediante el servidor
    async function saveServerDownloads() {
      if (!results.length) return;
      const rows = results.filter(r => !r.error).map(r => {
        const bp = r.bullet_points || [];
        return [
          r.ref || getRef(r.url),
          r.title || '',
          r.highlights || '',
          r.material || '-',
          r.color || '-',
          r.medidas || '-',
          r.peso_g ?? '',
          bp[0] || '',
          bp[1] || '',
          bp[2] || '',
          bp[3] || '',
          bp[4] || '',
          r.description || '',
          r.backend_keywords || '',
          ...nodeExportValues(r)
        ].map(val => `"${safeCell(val).replace(/"/g, '""')}"`).join(',');
      });
      const csvContent = 'referencia,titulo,highlights,material,color,medidas,peso_producto_g,bullet_1,bullet_2,bullet_3,bullet_4,bullet_5,descripcion,backend_keywords,nodo_amazon_es,categoria_amazon,estado_nodo,confianza_nodo,motivo_nodo\n' + rows.join('\n');
      const filename = `amazon_listings_2026_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;

      try {
        const resp = await fetch('/api/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: csvContent, filename: filename })
        });
        const data = await resp.json();
        if (resp.ok) {
          alert(`✅ ${data.message}`);
        } else {
          throw new Error(data.error);
        }
      } catch (e) {
        alert(`❌ Error al guardar en ~/Downloads: ${e.message}`);
      }
    }

    // Copiar tabla completa al portapapeles (formato TSV para pegar directo en Excel)
    function copyTableClipboard() {
      if (!results.length) return;
      const lines = ["Referencia\tTítulo Amazon\tItem Highlights\tMaterial\tColor\tMedidas\tPeso del producto (g)\tBullet 1\tBullet 2\tBullet 3\tBullet 4\tBullet 5\tDescripción\tBackend Keywords\tNodo Amazon.es\tCategoría Amazon\tEstado nodo\tConfianza nodo\tMotivo nodo"];
      results.filter(r => !r.error).forEach(r => {
        lines.push([r.ref || getRef(r.url), r.title, r.highlights, r.material, r.color || '-', r.medidas, r.peso_g ?? '',
          ...Array.from({length: 5}, (_, i) => r.bullet_points?.[i] || ''), r.description, r.backend_keywords || '', ...nodeExportValues(r)]
          .map(value => safeCell(value).replace(/[\t\r\n]+/g, ' ')).join('\t'));
      });
      navigator.clipboard.writeText(lines.join('\n')).then(() => {
        showToast("Tabla copiada (pega directo con Ctrl+V en Excel)");
      }).catch(() => alert('No se pudo copiar. Comprueba los permisos del portapapeles.'));
    }

    function updateResultsSummary() {
      if (isProcessing) return;
      const errors = results.filter(r => r.error).length;
      const review = results.filter(r => !r.error && !['asignado', 'manual'].includes(r.node_status)).length;
      $('retryBtn').classList.toggle('hidden', errors === 0);
      $('progressLabel').textContent = results.length ? `${results.length - errors} fichas generadas; ${errors} errores; ${review} nodos por revisar.` : '';
    }

    function nodeExportValues(item) {
      return [String(item.node_id || ''), item.node_path || '', item.node_status || 'pendiente',
        item.node_confidence || '', item.node_reason || ''];
    }

    function nodeListing(item) {
      return {title: item.title || '', highlights: item.highlights || '', material: item.material || '',
        color: item.color || '', medidas: item.medidas || '', description: item.description || '',
        bullet_points: item.bullet_points || [], backend_keywords: item.backend_keywords || '',
        product_type: item.product_type || '',
        node_search_terms: item.node_search_terms || []};
    }

    function invalidateNode(index) {
      const item = results[index];
      if (!item || item.error) return;
      Object.assign(item, {node_id: '', node_path: '', node_confidence: '', node_status: 'pendiente',
        node_reason: 'Ficha editada. Recalcula el nodo para clasificar la versión actual.',
        product_type: '', node_search_terms: [], node_candidates: []});
      renderNode(index);
      updateResultsSummary();
    }

    function renderNode(index) {
      const cell = $(`cell-node-${index}`), item = results[index];
      if (!cell || !item) return;
      if (item.error) { cell.textContent = 'Pendiente de generar la ficha'; return; }
      const busy = item.node_status === 'buscando';
      const good = ['asignado', 'manual'].includes(item.node_status);
      const candidates = item.node_candidates || [];
      cell.innerHTML = `
        <div class="space-y-2 text-xs">
          <div class="font-mono font-bold ${good ? 'text-emerald-800' : 'text-amber-800'}">${busy ? '<span class="spinner"></span>Buscando categoría…' : escHtml(item.node_id || 'Sin nodo asignado')}</div>
          <div class="text-gray-700">${escHtml(item.node_path || '')}</div>
          <div class="font-medium ${good ? 'text-emerald-700' : 'text-amber-700'}">${escHtml(item.node_status || 'pendiente')}${item.node_confidence ? ' · confianza ' + escHtml(item.node_confidence) : ''}</div>
          <div class="text-gray-500">${escHtml(item.node_reason || 'Se asignará después de generar la ficha.')}</div>
          <button type="button" onclick="recalculateNode(${index})" ${isProcessing ? 'disabled' : ''} class="node-action px-2 py-1 rounded border border-indigo-200 text-indigo-700 disabled:opacity-50">Recalcular nodo</button>
          <details>
            <summary class="cursor-pointer text-indigo-700">Revisar o elegir otra categoría</summary>
            <label class="block mt-2" for="node-select-${index}">Nodos del Excel</label>
            <select id="node-select-${index}" aria-label="Nodo Amazon de la fila ${index + 1}" onchange="chooseNode(${index}, this.value)" ${isProcessing ? 'disabled' : ''} class="w-full max-w-sm border rounded p-1 mt-1">
              <option value="">Sin asignar</option>
              ${candidates.map(n => `<option value="${escHtml(n.id)}" ${n.id === item.node_id ? 'selected' : ''}>${escHtml(n.id + ' · ' + n.path)}</option>`).join('')}
            </select>
            <label class="block mt-2" for="node-search-${index}">Buscar en todo el catálogo</label>
            <input id="node-search-${index}" maxlength="200" placeholder="Ej.: jarrones, portavelas…" ${isProcessing ? 'disabled' : ''} class="w-full border rounded p-1 mt-1">
            <button type="button" onclick="searchNodes(${index})" ${isProcessing ? 'disabled' : ''} class="node-action mt-1 text-indigo-700 underline">Buscar categorías</button>
          </details>
        </div>`;
    }

    async function nodeRequest(payload) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), payload.action === 'search_nodes' ? 15000 : 460000);
      try {
        const resp = await fetch('/api/generate', {method: 'POST', signal: controller.signal,
          headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
        const data = await resp.json().catch(() => { throw new Error(`Respuesta no válida (HTTP ${resp.status})`); });
        if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        return data;
      } catch (e) {
        if (e.name === 'AbortError') throw new Error('La búsqueda del nodo tardó demasiado. Puedes recalcularlo sin repetir la ficha.');
        throw e;
      } finally { clearTimeout(timeout); }
    }

    async function assignNode(index, apiKey) {
      const item = results[index];
      const listing = nodeListing(item);
      const snapshot = JSON.stringify(listing);
      item.node_status = 'buscando';
      item.node_reason = 'Comparando el tipo de producto con las categorías del Excel.';
      renderNode(index);
      try {
        const data = await nodeRequest({action: 'map_node', provider: currentProvider, api_key: apiKey,
          image_url: item.url, name: item.name || '', dimensions: item.rawDims || '', listing,
          model: currentProvider === 'gemini' ? ($('geminiModel').value.trim() || 'gemini-2.5-flash') : ''});
        if (JSON.stringify(nodeListing(item)) !== snapshot) { invalidateNode(index); return; }
        Object.assign(item, data);
      } catch (error) {
        Object.assign(item, {node_id: '', node_path: '', node_status: 'error', node_confidence: '',
          node_reason: error.message, node_candidates: []});
      }
      renderNode(index);
    }

    async function runNodeTask(index, task) {
      if (isProcessing || !results[index] || results[index].error) return;
      isProcessing = true;
      const locked = [...document.querySelectorAll('input, textarea, select, button')].map(el => [el, el.disabled]);
      const editable = [...document.querySelectorAll('[contenteditable]')].map(el => [el, el.contentEditable]);
      locked.forEach(([el]) => el.disabled = true);
      editable.forEach(([el]) => el.contentEditable = 'false');
      try { await task(); }
      catch (error) { alert('No se pudo buscar el nodo: ' + error.message); }
      finally {
        isProcessing = false;
        locked.forEach(([el, disabled]) => el.disabled = disabled);
        editable.forEach(([el, value]) => el.contentEditable = value);
        results.forEach((_, i) => renderNode(i));
        updateResultsSummary();
      }
    }

    async function recalculateNode(index) {
      return runNodeTask(index, () => assignNode(index, $('apiKey').value.trim()));
    }

    async function searchNodes(index) {
      const query = $(`node-search-${index}`).value.trim();
      if (!query) return;
      return runNodeTask(index, async () => {
        const data = await nodeRequest({action: 'search_nodes', query});
        const item = results[index];
        item.node_candidates = data.nodes;
        if (item.node_id && !data.nodes.some(n => n.id === item.node_id))
          item.node_candidates.unshift({id: item.node_id, path: item.node_path});
        renderNode(index);
        $(`cell-node-${index}`).querySelector('details').open = true;
        if (!data.nodes.length) showToast('No se encontraron categorías. Prueba un sinónimo.');
      }).then(() => { const details = $(`cell-node-${index}`)?.querySelector('details'); if (details) details.open = true; });
    }

    function chooseNode(index, id) {
      if (isProcessing) return;
      const item = results[index];
      const node = (item.node_candidates || []).find(n => n.id === id);
      if (id && !node) return;
      Object.assign(item, {node_id: node?.id || '', node_path: node?.path || '',
        node_status: node ? 'manual' : 'revisar', node_confidence: '',
        node_reason: node ? 'Categoría elegida manualmente del catálogo Excel.' : 'Nodo retirado para revisión.'});
      renderNode(index);
      updateResultsSummary();
    }

    function safeCell(value) {
      const text = String(value ?? '');
      return /^[\s]*[=+@-]/.test(text) ? "'" + text : text;
    }

    $('urlsInput').addEventListener('input', () => { window.pendingData = null; });
    window.addEventListener('beforeunload', event => {
      if (isProcessing) { event.preventDefault(); event.returnValue = ''; }
    });
    // Inicializar
    setProvider('gemini');
