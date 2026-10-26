const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync(__dirname + '/../index.html', 'utf8');
const scripts = [...source.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(x => x[1]);
const stored = new Map();
const elements = {};
const alerts = [];
const ui = id => elements[id] ??= {innerHTML:'', value:'', style:{}};
const sandbox = {
  document: {getElementById:ui, addEventListener:()=>{}, querySelector:()=>null},
  localStorage: {getItem:k=>stored.get(k)??null, setItem:(k,v)=>stored.set(k,v)},
  crypto: require('node:crypto').webcrypto,
  alert:m=>alerts.push(m), confirm:()=>true,
  window:{print:()=>{}}, URL, Blob, Date, Intl, Math, Number, String, JSON,
  setTimeout, console,
};
vm.createContext(sandbox);
vm.runInContext(scripts[0],sandbox);
const run = x => vm.runInContext(x,sandbox);
const event = fields => {const elements=Object.fromEntries(Object.entries(fields).map(([k,v])=>[k,{value:String(v)}]));elements.namedItem=name=>elements[name];return {preventDefault(){},target:{elements}}};

assert.equal(run('db.products.length'),0,'new business starts without sample products');
assert.equal(run('db.sales.length'),0);
assert.match(ui('nav').innerHTML,/Tributos/);
sandbox.addProduct(event({id:'P1',name:'Producto',category:'General',price:100,cost:40,stock:10,min:2}));
sandbox.addService(event({id:'S1',name:'Servicio',category:'General',price:50,cost:10,detail:'Mano de obra'}));
sandbox.cartAdd(event({item:'P:P1',qty:2}));
sandbox.cartAdd(event({item:'S:S1',qty:1}));
sandbox.checkout(event({method:'Mixto',cashAmount:100,transferAmount:100,cardAmount:50,seller:'Principal'}));
assert.equal(run('db.products[0].stock'),8);
assert.equal(run('db.sales.length'),2);
assert.equal(run('totals().revenue'),250);
assert.equal(run('totals().cogs'),90);
assert.equal(run('totals().cash'),100);
assert.equal(run('totals().bank'),150);
const saleId = run('db.sales[0].id');
sandbox.refund(event({id:saleId,qty:1}));
assert.equal(run('db.products[0].stock'),9);
assert.equal(run('totals().revenue'),150);
assert.equal(run('totals().cogs'),50);
assert.equal(run('totals().cash'),60);
assert.equal(run('totals().bank'),90);
assert.deepEqual(JSON.parse(JSON.stringify(run('db.refundEvents[0].allocation'))),{Efectivo:40,Transferencia:40,Tarjeta:20});
run("report='ingresos'");
const incomes = run('reportData().rows');
assert.equal(incomes[3][2],run('money(150)'));
assert.equal(incomes[0][2],run('money(60)'));
assert.equal(incomes[1][2],run('money(60)'));
assert.equal(incomes[2][2],run('money(30)'));
run("report='resultado'");
assert.equal(run('reportData().rows.at(-1)[1]'),run('money(100)'));
run("go('Ventas')");
assert.match(ui('main').innerHTML,/Devoluciones/);
run(`receipt(${JSON.stringify(saleId)})`);
assert.match(ui('printArea').innerHTML,/Servicio/,'receipt prints all lines');
assert.match(ui('printArea').innerHTML,/Producto/);
run("go('Productos')");
assert.match(ui('main').innerHTML,/Actualizar ficha de producto/);
sandbox.updateProduct(event({id:'P1',name:'Producto editado',category:'Nuevo',price:120,cost:45,min:3}));
assert.equal(run('db.products[0].price'),120);
assert.equal(run('db.sales[0].total'),200,'historical sale is not repriced');
assert.equal(run('db.products[0].stock'),9);
run("go('Servicios')");
assert.match(ui('main').innerHTML,/Actualizar ficha de servicio/);
sandbox.updateService(event({id:'S1',name:'Servicio editado',category:'Nuevo',price:60,cost:20,detail:'Actualizado'}));
assert.equal(run('db.services[0].price'),60);
assert.equal(run('db.sales[1].total'),50,'historical service is not repriced');
sandbox.addProduct(event({id:'P:2',name:'Código con dos puntos',category:'General',price:10,cost:5,stock:1,min:0}));
sandbox.cartAdd(event({item:'P:P:2',qty:1}));
assert.equal(run('cart[0].id'),'P:2');
run('cart=[]');
run("go('Gastos')");
sandbox.addExpense(event({amount:30,method:'Efectivo',concept:'Transporte',category:'Operativo'}));
assert.equal(run('totals().profit'),70);
assert.equal(run('totals().cash'),30);
run("go('Tributos')");
assert.match(ui('main').innerHTML,/Libro auxiliar/);
assert.match(ui('main').innerHTML,/150.00 CUP/);
stored.set('jb360_actor_profile_v08',JSON.stringify({actor:'tcp',business:'Negocio Uno'}));
let exported;
sandbox.download=(blob,name)=>{exported={blob,name}};
sandbox.backup();
assert.equal(exported.name.startsWith('jb360-respaldo-'),true);
exported.blob.text().then(text=>{
  const backup=JSON.parse(text);
  assert.equal(backup.data.products[0].stock,9);
  assert.equal(backup.actorProfile.business,'Negocio Uno');
  console.log('PASS: gastos, libro auxiliar, respaldo con perfil');
}).catch(e=>{console.error(e);process.exitCode=1});
assert.ok(stored.has('jb360_demo_v1'));
assert.equal(alerts.length,1,'only sale confirmation is shown');
console.log('PASS: initial state, product/service, mixed sale, proportional refund, stock, cash, bank, reports, receipt, catalog edits, persistence');

// A service-only receipt must appear as a service in all general reports.
// Product and service codes are separate catalogs and may overlap.
run('db=seed();cart=[]');
sandbox.addProduct(event({id:'X',name:'Producto X',category:'General',price:200,cost:80,stock:5,min:0}));
sandbox.addService(event({id:'X',name:'Servicio X',category:'General',price:120,cost:30,detail:'Insumos'}));
sandbox.cartAdd(event({item:'S:X',qty:2}));
sandbox.checkout(event({method:'Efectivo',cashAmount:0,transferAmount:0,cardAmount:0,seller:'Principal'}));
assert.equal(run('db.sales[0].kind'),'service');
assert.equal(run('db.products[0].stock'),5);
run("report='ventas'");
assert.deepEqual(Array.from(run('reportData().heads')).slice(1,4),['Operación','Tipo','Concepto']);
assert.deepEqual(Array.from(run('reportData().rows[0]')).slice(1,3),['Venta','Servicio']);
run("report='servicios'");
assert.equal(run('reportData().rows[0][2]'),run('money(240)'));
assert.equal(run('reportData().rows[0][3]'),run('money(60)'));
run("report='productos'");
assert.equal(run('reportData().rows.length'),0);
run("report='ingresos'");
assert.equal(run('reportData().rows[0][1]'),1);
sandbox.refund(event({id:run('db.sales[0].id'),qty:1}));
assert.equal(run('db.products[0].stock'),5,'service refund cannot restore product stock with the same code');
assert.equal(run('db.inventory.filter(x=>x.type===\'devolucion\').length'),0);
assert.equal(run('totals().revenue'),120);
assert.equal(run('totals().cogs'),30);
run("report='ventas'");
assert.deepEqual(Array.from(run('reportData().rows[1]')).slice(1,3),['Devolución','Servicio']);
run("report='costos'");
assert.equal(run('reportData().rows[0][0]'),'Servicio');
run("report='servicios'");
assert.equal(run('reportData().rows[0][2]'),run('money(120)'));
assert.equal(run('reportData().rows[0][3]'),run('money(30)'));
sandbox.exportAuxBook('ingresos');
exported.blob.text().then(csv=>{
  assert.match(csv,/"Operación";"Tipo"/);
  assert.match(csv,/"Venta";"Servicio"/);
  assert.match(csv,/"Devolución";"Servicio"/);
  console.log('PASS: sale and refund of service-only receipt, categorized reports and CSV, catalog code collision');
}).catch(e=>{console.error(e);process.exitCode=1});
