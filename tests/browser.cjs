const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
 const browser = await chromium.launch({headless:true});
 try {
 for (const path of ['index.html','amazon-titulos.html']) {
  const page = await browser.newPage();
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('dialog',d=>d.dismiss());
  let calls=0, nodeCalls=0;
  await page.route('https://example.com/**',r=>r.fulfill({status:404,body:''}));
  await page.route('https://example.com/one.jpg',r=>r.fulfill({contentType:'image/png',body:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aE1cAAAAASUVORK5CYII=','base64')}));
  await page.route('**/api/generate', async route=>{
   const request = route.request().postDataJSON();
   if (request.action === 'search_nodes') return route.fulfill({json:{nodes:[{id:'2844384031',path:'/Categorías/Decoración del hogar/Jarrones'}]}});
   if (request.action === 'map_node') {
    nodeCalls++;
    if(nodeCalls===1) return route.fulfill({status:502,json:{error:'Fallo temporal de clasificación'}});
    return route.fulfill({json:{node_id:'2822771031',node_path:'/Categorías/Muebles/Comedor/Mesas',node_status:'asignado',node_confidence:'alta',node_reason:'Mesa de comedor',product_type:'Mesa',node_candidates:[{id:'2822771031',path:'/Categorías/Muebles/Comedor/Mesas'}]}});
   }
   calls++;
   if(calls===2) return route.fulfill({status:429,json:{error:'Cuota temporal'}});
   await new Promise(r=>setTimeout(r,50));
   return route.fulfill({json:{title:'Mesa de madera',peso_g:265,highlights:'Uso interior',material:'Madera',medidas:'10x20 cm',bullet_points:['Uno','Dos','Tres','Cuatro','Cinco'],description:'Descripción de prueba'}});
  });
  await page.goto('http://127.0.0.1:8799/'+path);
  await page.waitForFunction(()=>typeof processImages==='function');
  await page.waitForFunction(()=>typeof XLSX!=='undefined');
  const previewExcel = await page.evaluate(()=>{
   const wb=XLSX.utils.book_new();
   const ws=XLSX.utils.aoa_to_sheet([
    ['Número de producto','URL'],
    [123,'https://example.com/one.jpg'],
    ['<script>bad()</script>','javascript:alert(1)'],
    ['REF-3','https://example.com/missing.jpg']
   ]);
   ws.A2.z='000000';
   XLSX.utils.book_append_sheet(wb,ws,'Productos');
   return Array.from(new Uint8Array(XLSX.write(wb,{type:'array',bookType:'xlsx'})));
  });
  await page.setInputFiles('#imagePreviewInput',{name:'vista.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:Buffer.from(previewExcel)});
  await page.waitForFunction(()=>document.querySelectorAll('#imagePreviewList li').length===3);
  assert.equal(await page.locator('#imagePreviewList li > span').first().textContent(),'000123');
  await page.locator('#imagePreviewList img').first().scrollIntoViewIfNeeded();
  await page.waitForFunction(()=>document.querySelector('#imagePreviewList img').naturalWidth>0);
  assert.equal(await page.locator('#imagePreviewList script').count(),0);
  assert.equal(await page.locator('#imagePreviewList li').nth(1).locator('img').count(),0);
  await page.waitForFunction(()=>document.querySelector('#imagePreviewList').textContent.includes('No se pudo cargar la imagen'));
  assert.equal(calls,0);
  assert.equal(nodeCalls,0);
  assert.equal(await page.evaluate(()=>results.length),0);
  assert.equal(await page.inputValue('#urlsInput'),'');
  assert.equal(await page.evaluate(()=>window.pendingData || null),null);
  await page.getByRole('button',{name:'Vaciar listado'}).click();
  assert.equal(await page.locator('#imagePreviewList li').count(),0);
  await page.setInputFiles('#imagePreviewInput',{name:'sin-cabecera.csv',mimeType:'text/csv',buffer:Buffer.from('REF-9,https://example.com/9.jpg\n')});
  await page.waitForFunction(()=>document.querySelectorAll('#imagePreviewList li').length===1);
  assert.equal(await page.locator('#imagePreviewList li > span').textContent(),'REF-9');
  await page.evaluate(()=>{setProvider('openai');sleep=()=>Promise.resolve();});
  await page.fill('#apiKey','dummy');
  await page.fill('#urlsInput','https://example.com/one.jpg?token=1\nhttps://example.com/two.jpg');
  await page.click('#processBtn');
  await page.waitForFunction(()=>!isProcessing && results.length===2);
  assert.equal(calls,2);
  assert.equal(await page.locator('#cell-peso-0 input').inputValue(),'265');
  await page.locator('#cell-peso-0 input').fill('275');
  assert.equal(await page.evaluate(()=>results[0].peso_g),275);
  assert.equal(await page.evaluate(()=>results[0].node_status),'error');
  assert.equal(await page.evaluate(()=>results[0].title),'Mesa de madera');
  await page.evaluate(()=>recalculateNode(0));
  assert.equal(await page.evaluate(()=>results[0].node_id),'2822771031');
  assert.equal(calls,2);
  assert.equal(nodeCalls,2);
  assert.equal(await page.locator('#resultsBody tr').count(),2);
  assert.equal(await page.evaluate(()=>results.filter(r=>r.error).length),1);
  await page.click('#retryBtn');
  await page.waitForFunction(()=>!isProcessing && results.every(r=>!r.error));
  assert.equal(calls,3);
  assert.equal(await page.locator('#imagePreviewList li > span').textContent(),'REF-9');
  await page.locator('#title-text-0').fill('Título editado');
  assert.equal(await page.evaluate(()=>results[0].title),'Título editado');
  assert.equal(await page.evaluate(()=>results[0].node_id),'');
  await page.evaluate(()=>recalculateNode(0));
  assert.equal(await page.evaluate(()=>results[0].node_id),'2822771031');
  if(path==='index.html') {
   await page.click('#supplier-tab-dcasa');
   assert.equal(await page.locator('#resultsBody tr').count(),0);
   await page.click('#supplier-tab-signes');
   assert.equal(await page.locator('#resultsBody tr').count(),2);
   assert.equal((await page.locator('#title-text-0').innerText()).trim(),'Título editado');
  }
  const dims=await page.evaluate(()=>['100x200 cm','100x200 mm','1 m x 20 cm x 50 mm','100x200'].map(parseDimensions));
  assert.deepEqual(dims,['100x200 cm','10x20 cm','100x20x5 cm','-']);
  assert.equal(await page.evaluate(()=>extractMaterialFromText('cuero sintético')),'Piel sintética');
  assert.equal(await page.evaluate(()=>getRef('https://example.com/abc.jpg?secret=x')),'abc');
  assert.equal(await page.evaluate(()=>safeCell('=1+1')),"'=1+1");
  await page.waitForFunction(()=>typeof XLSX!=='undefined',{timeout:15000});
  const exported=await page.evaluate(()=>{
   let wb;XLSX.writeFile=b=>wb=b;exportExcel();return XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]],{header:1});
  });
  assert.equal(exported[0].length,24);assert.equal(exported[1].length,24);assert.equal(exported[1][1],'Título editado');
  assert.equal(exported[0][6],'Peso del producto (g)');
  assert.equal(exported[1][6],275);
  assert.equal(exported[1][19],'2822771031');
  const tsv = await page.evaluate(async () => {
    let text; navigator.clipboard.writeText = async value => {text=value};
    copyTableClipboard(); return text;
  });
  assert.equal(tsv.split('\n')[0].split('\t').length,19);
  assert.equal(tsv.split('\n')[1].split('\t')[14],'2822771031');
  const downloadEvent = page.waitForEvent('download');
  await page.evaluate(()=>exportCSVLocal());
  const download = await downloadEvent;
  const chunks=[];for await (const chunk of await download.createReadStream()) chunks.push(chunk);
  const csv=Buffer.concat(chunks).toString('utf8');
  assert.ok(csv.includes('nodo_amazon_es,categoria_amazon,estado_nodo'));
  assert.ok(csv.includes('"2822771031"'));

  await page.locator('#cell-node-0 summary').click();
  await page.fill('#node-search-0','jarrones');
  await page.evaluate(()=>searchNodes(0));
  await page.selectOption('#node-select-0','2844384031');
  assert.equal(await page.evaluate(()=>results[0].node_status),'manual');
  assert.equal(await page.evaluate(()=>nodeExportValues(results[0])[0]),'2844384031');
  await page.setInputFiles('#fileInput',{name:'products.csv',mimeType:'text/csv',buffer:Buffer.from('URL,Nombre,Medidas\nhttps://example.com/three.jpg,Mesa,100x200 mm\n')});
  await page.waitForFunction(()=>window.pendingData?.length===1);
  assert.equal(await page.evaluate(()=>pendingData[0].dims),'10x20 cm');
  await page.fill('#urlsInput','https://example.com/four.jpg');
  assert.equal(await page.evaluate(()=>window.pendingData),null);
  assert.deepEqual(errors,[]);
  console.log('PASS '+path+': previsualización independiente XLSX/CSV, ceros iniciales, imagen cargada, URL inválida, imagen fallida, limpieza y flujo de generación existente');
  await page.close();
 }
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
