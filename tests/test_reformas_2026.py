import asyncio
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from datetime import date, timedelta
from decimal import Decimal

# Never use the user's operational database.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations
from starlette.requests import Request
from app.core.database import Base
import app.models
from app.models.campeonato import Campeonato
from app.models.categoria import Categoria
from app.models.fecha import Fecha
from app.models.jinete import Jinete
from app.models.jinete_campeonato import JineteCampeonato
from app.models.jinete_fecha import JineteFecha
from app.models.caballo import Caballo
from app.models.sorteo import Sorteo, SorteoDetalle
from app.models.resultado import ResultadoCategoria, ResultadoDetalle
from app.models.tv_salida import TvSalida
from app.services.clasificacion import POLITICA, evaluar_categoria, recalcular_categoria, habilitado, ausencias_consecutivas, estados_publicos
from app.routers import tv, resultados, publico, inscripciones, acreditacion


def request(path='/tv', form=None):
    req = Request({'type': 'http', 'method': 'POST', 'path': path, 'root_path': '', 'scheme': 'http', 'server': ('test', 80), 'headers': [], 'query_string': b'', 'session': {'usuario_id': 1, 'usuario_rol': 'MASTER', 'usuario_nombre': 'Prueba'}})
    if form is not None:
        from starlette.datastructures import FormData
        req._form = FormData(form)
    return req


class ReglasTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, autoflush=False)
        self.camp = Campeonato(nombre='Campeonato', estado='activo', publicado=True)
        self.db.add(self.camp); self.db.flush()
        self.cat = Categoria(campeonato_id=self.camp.id, nombre='Bastos', puntua_campeonato=True)
        self.db.add(self.cat); self.db.flush()
        self.fechas = [Fecha(campeonato_id=self.camp.id, nombre=f'F{i+1}', fecha=date(2026, 1+i, 1), localidad='Río Negro', inscripcion_cerrada=True) for i in range(4)]
        self.jinetes = [Jinete(nombres=f'Jinete{i}', apellidos='Prueba', dni=str(i)) for i in range(4)]
        self.caballo = Caballo(nombre='Caballo')
        self.db.add_all(self.fechas+self.jinetes+[self.caballo]);self.db.flush()
        self.pres = [JineteCampeonato(campeonato_id=self.camp.id, categoria_id=self.cat.id, jinete_id=j.id) for j in self.jinetes]
        self.db.add_all(self.pres);self.db.commit()

    def tearDown(self):
        self.db.close();self.engine.dispose()

    def carga(self, numero, puntos, estado='publicado', categoria=None):
        cat = categoria or self.cat
        sorteo = Sorteo(fecha_id=self.fechas[numero-1].id, categoria_id=cat.id, cantidad_caballos_sorteados=4)
        self.db.add(sorteo);self.db.flush()
        carga = ResultadoCategoria(sorteo_id=sorteo.id, estado=estado)
        self.db.add(carga);self.db.flush()
        for i, valor in enumerate(puntos):
            d = SorteoDetalle(sorteo_id=sorteo.id, jinete_id=self.jinetes[i].id, caballo_id=self.caballo.id, orden=i+1, palenque=1, caballo_nombre='Caballo', jinete_nombre=f'Jinete{i}')
            self.db.add(d);self.db.flush()
            self.db.add(ResultadoDetalle(resultado_categoria_id=carga.id, sorteo_detalle_id=d.id, puntos=valor))
        self.db.commit()
        return carga

    def estado(self):
        return [evaluar_categoria(self.db,self.camp.id,self.cat.id).get(j.id,(None,None))[0] for j in self.jinetes]

    def confirmar_repechaje(self, valores, confirmar=True):
        from app.routers.repechaje import contexto, guardar
        cat, totales, firma, jinetes, planilla = contexto(request(), self.cat.id, self.db, True)
        guardar(self.db, cat, totales, firma, jinetes, planilla, firma, valores, confirmar, 'Prueba')

    def test_repechaje_independiente_no_acumula(self):
        from app.services.resultados import posiciones_campeonato
        from app.services.clasificacion import bloqueo_sorteo
        self.carga(1,[0,1,2,5]);self.carga(2,[0]*4)
        antes=posiciones_campeonato(self.db,self.camp.id,self.cat.id)
        self.assertIsNotNone(bloqueo_sorteo(self.db,self.fechas[2],self.cat))
        self.confirmar_repechaje({str(self.jinetes[1].id):'.01',str(self.jinetes[2].id):'0'})
        self.assertEqual(self.estado(),['descalificado','activo','descalificado','activo'])
        self.assertIsNone(bloqueo_sorteo(self.db,self.fechas[2],self.cat))
        despues=posiciones_campeonato(self.db,self.camp.id,self.cat.id)
        self.assertEqual([x['puntos'] for x in antes],[x['puntos'] for x in despues])

    def test_repechaje_borrador_faltantes_y_sanciones(self):
        from fastapi import HTTPException
        self.carga(1,[1]*4);self.carga(2,[0]*4)
        valores={str(j.id):'1' for j in self.jinetes};valores[str(self.jinetes[0].id)]=''
        self.confirmar_repechaje(valores,False)
        self.assertEqual(self.estado(),['repechaje']*4)
        with self.assertRaises(HTTPException):self.confirmar_repechaje(valores)
        valores[str(self.jinetes[0].id)]='1'
        self.jinetes[0].estado='descalificado';self.jinetes[0].estado_causa='ausencias_consecutivas';self.db.commit()
        self.confirmar_repechaje(valores)
        self.assertFalse(habilitado(self.db,self.jinetes[0],self.fechas[2],self.cat.id))
        self.assertEqual(self.jinetes[0].estado_causa,'ausencias_consecutivas')

    def test_cambio_base_invalida_repechaje(self):
        from app.services.clasificacion import bloqueo_sorteo
        self.carga(1,[1]*4);c=self.carga(2,[0]*4)
        self.confirmar_repechaje({str(j.id):'1' for j in self.jinetes})
        c.detalles[0].puntos=1;self.db.commit()
        self.assertIsNotNone(bloqueo_sorteo(self.db,self.fechas[2],self.cat))
        self.assertEqual(self.estado(),['repechaje']*4)

    def test_bloqueo_real_sorteo_f3(self):
        from app.routers.sorteos import realizar_sorteo
        from fastapi import HTTPException
        self.carga(1,[1]*4);self.carga(2,[0]*4)
        with self.assertRaises(HTTPException) as e:
            realizar_sorteo(self.fechas[2].id,self.cat.id,request(),db=self.db)
        self.assertEqual(e.exception.status_code,409)
        self.assertIn('Repechaje pendiente',e.exception.detail)

    def test_repechaje_reabrir_y_bloqueo_posterior(self):
        from app.routers.repechaje import reabrir
        from app.services.clasificacion import bloqueo_sorteo
        from fastapi import HTTPException
        self.carga(1,[1]*4);self.carga(2,[0]*4)
        valores={str(j.id):'1' for j in self.jinetes}
        self.confirmar_repechaje(valores)
        reabrir(request(),self.cat.id,self.db)
        self.assertIsNotNone(bloqueo_sorteo(self.db,self.fechas[2],self.cat))
        self.confirmar_repechaje(valores)
        self.carga(3,[1]*4)
        with self.assertRaises(HTTPException):reabrir(request(),self.cat.id,self.db)

    def test_repechaje_validacion_puntos(self):
        from app.routers.repechaje import puntaje
        from fastapi import HTTPException
        for valor in ['-1','NaN','Infinity','.001','100000000','texto']:
            with self.assertRaises(HTTPException):puntaje(valor)
        self.assertEqual(puntaje('0,01'),'0.01')

    def test_repechaje_excel_y_panel(self):
        from app.routers.repechaje import exportar,importar,panel,cargar
        from fastapi import UploadFile
        from openpyxl import load_workbook
        self.carga(1,[0,1,2,5]);self.carga(2,[0]*4)
        resp=exportar(request(),self.cat.id,self.db)
        async def contenido():return b''.join([x async for x in resp.body_iterator])
        wb=load_workbook(io.BytesIO(asyncio.run(contenido())))
        wb.active['B2']=1;wb.active['B3']=0
        out=io.BytesIO();wb.save(out);out.seek(0)
        asyncio.run(importar(request(),self.cat.id,UploadFile(file=out,filename='planilla.xlsx'),self.db))
        self.assertEqual(self.estado(),['descalificado','repechaje','repechaje','activo'])
        response=panel(request(),self.cat.id,self.db)
        self.assertIn(b'Confirmar repechaje',response.body)
        self.confirmar_repechaje({str(self.jinetes[1].id):'1',str(self.jinetes[2].id):'0'})
        self.assertIn(b'PASA A F3',panel(request(),self.cat.id,self.db).body)

    def test_asistencia_provisional_y_exclusion_repechaje(self):
        from app.routers.repechaje import reabrir
        self.carga(1,[1]*4);self.carga(2,[0]*4)
        estados=['validado','pendiente','validado','no_habilitado']
        filas=[]
        for j,estado in zip(self.jinetes,estados):
            fila=JineteFecha(jinete_id=j.id,fecha_id=self.fechas[2].id,categoria_id=self.cat.id,estado=estado,motivo_no_habilitado='suspendido' if estado=='no_habilitado' else None)
            filas.append(fila);self.db.add(fila)
        self.db.commit()
        self.assertTrue(habilitado(self.db,self.jinetes[0],self.fechas[2],self.cat.id))
        self.confirmar_repechaje({str(j.id):'1' if i==2 else '0' for i,j in enumerate(self.jinetes)})
        self.assertEqual([f.estado for f in filas],['no_habilitado','no_habilitado','validado','no_habilitado'])
        self.assertEqual(filas[3].motivo_no_habilitado,'suspendido')
        reabrir(request(),self.cat.id,self.db)
        self.assertEqual([f.estado for f in filas],estados)
        self.confirmar_repechaje({str(j.id):'1' for j in self.jinetes})
        self.assertEqual([f.estado for f in filas],estados)

    def test_limites(self):
        self.carga(1,[0,Decimal('.01'),2,3]);self.carga(2,[0,0,Decimal('2.99'),2])
        self.assertEqual(self.estado(),['descalificado','repechaje','repechaje','activo'])

    def test_f3_no_resuelve_repechaje(self):
        self.carga(1,[0,1,2,5]);self.carga(2,[0,0,0,0]);self.carga(3,[10,Decimal('.01'),0,0])
        self.assertEqual(self.estado(),['descalificado','repechaje','repechaje','activo'])

    def test_falta_f2_no_saltar_a_f3(self):
        self.carga(1,[0,1,2,5]);self.carga(3,[0,1,2,5])
        self.assertEqual(self.estado(),[None]*4)

    def test_incompletos_no_cero(self):
        self.carga(1,[0,1,2,5]);self.carga(2,[None,0,0,0])
        self.assertEqual(self.estado(),[None]*4)

    def test_categoria_independiente(self):
        otra=Categoria(campeonato_id=self.camp.id,nombre='Clina');self.db.add(otra);self.db.commit()
        self.carga(1,[0,1,2,5]);self.carga(2,[10,10,10,10],categoria=otra)
        self.assertEqual(self.estado(),[None]*4)

    def test_no_puntua(self):
        self.carga(1,[0]*4);self.carga(2,[0]*4);self.cat.puntua_campeonato=False;self.db.commit()
        self.assertEqual(self.estado(),[None]*4)

    def test_no_levanta_sanciones(self):
        self.carga(1,[1]*4);self.carga(2,[1]*4)
        for j,causa in zip(self.jinetes,['ausencias_consecutivas','manual','limite_suspensiones','historica_sin_causa']):
            j.estado='descalificado';j.estado_causa=causa
        self.db.commit();recalcular_categoria(self.db,self.camp.id,self.cat.id);self.db.commit()
        self.assertTrue(all(j.estado=='descalificado' for j in self.jinetes))
        self.assertTrue(all(not habilitado(self.db,j,self.fechas[2],self.cat.id) for j in self.jinetes))

    def test_f4_bloqueada_hasta_resolver_repechaje(self):
        self.carga(1,[1]*4);self.carga(2,[0]*4)
        self.assertTrue(habilitado(self.db,self.jinetes[0],self.fechas[2],self.cat.id))
        self.assertFalse(habilitado(self.db,self.jinetes[0],self.fechas[2],self.cat.id,para_sorteo=True))
        self.assertFalse(habilitado(self.db,self.jinetes[0],self.fechas[3],self.cat.id))
        self.confirmar_repechaje({str(j.id): '1' for j in self.jinetes})
        self.assertTrue(habilitado(self.db,self.jinetes[0],self.fechas[3],self.cat.id))

    def test_reabrir_quita_calculo_obsoleto(self):
        self.carga(1,[1]*4);c=self.carga(2,[0]*4,'finalizado')
        recalcular_categoria(self.db,self.camp.id,self.cat.id);self.db.commit()
        resultados.reabrir_resultado(request(),c.id,self.db)
        self.assertTrue(all(p.estado_clasificacion is None for p in self.pres))

    def test_no_filtra_puntos_sin_publicar(self):
        self.carga(1,[1]*4);self.carga(2,[0]*4,'finalizado')
        self.assertEqual(set(estados_publicos(self.db,self.camp.id,self.cat.id).values()),{'EN COMPETENCIA'})

    def test_ausencias_consecutivas(self):
        for f,estado in zip(self.fechas,['ausente','validado','ausente','ausente']):
            self.db.add(JineteFecha(fecha_id=f.id,jinete_id=self.jinetes[0].id,categoria_id=self.cat.id,estado=estado))
        self.db.commit()
        self.assertEqual(ausencias_consecutivas(self.db,self.jinetes[0].id,self.camp.id,self.fechas[2]),1)
        self.assertEqual(ausencias_consecutivas(self.db,self.jinetes[0].id,self.camp.id,self.fechas[3]),2)

    def test_fecha_publica_independiente(self):
        f=self.fechas[0];f.estado='programada';f.inscripcion_cerrada=False
        self.assertEqual(f.estado_publico,'FINALIZADA');self.assertEqual(f.estado,'programada');self.assertFalse(f.inscripcion_cerrada)
        for estado in ['suspendida','cancelada','reprogramada']:
            f.estado=estado;self.assertEqual(f.estado_publico,estado.upper())
        f.estado_publico_manual='en_curso';self.assertEqual(f.estado_publico,'EN_CURSO')

    def test_publicacion(self):
        self.assertIsNotNone(publico.campeonato_oficial_actual(self.db))
        self.camp.publicado=False;self.db.commit()
        self.assertIsNone(publico.campeonato_oficial_actual(self.db))

    def test_manual_preservada(self):
        from inspect import signature
        fn=inscripciones.agregar_jinete_manual_fecha_cerrada if hasattr(inscripciones,'agregar_jinete_manual_fecha_cerrada') else None
        funcs=[r.endpoint for r in inscripciones.router.routes if 'manual' in r.path and 'POST' in r.methods]
        self.assertTrue(funcs)
        # Use the actual patched endpoint, respecting closed-date constraints.
        fn=funcs[0]
        params={'request':request(),'fecha_id':self.fechas[0].id,'jinete_campeonato_id':self.pres[0].id,'db':self.db}
        response=fn(**{k:v for k,v in params.items() if k in signature(fn).parameters})
        self.assertEqual(response.status_code,303)
        ins=self.db.scalar(select(JineteFecha).where(JineteFecha.jinete_id==self.jinetes[0].id))
        self.assertIsNotNone(ins);self.assertEqual(ins.estado,'validado')

    def preparar_graph(self,sorteo,detalle):
        return tv.preparar_graph(request(),sorteo.id,detalle.id,'on','on','on','on',None,None,None,self.db)

    def test_tv_snapshot_independiente_y_vacio(self):
        c=self.carga(1,[1]*4);sorteo=c.sorteo;d=sorteo.detalles
        salida=tv.obtener_o_crear_salida(self.db);token=salida.token
        self.preparar_graph(sorteo,d[0]);tv.cambiar_aire(request(),'graph',1,None,self.db)
        primero=salida.graph_pgm
        self.preparar_graph(sorteo,d[1]);self.assertEqual(salida.graph_pgm,primero)
        tv.preparar_salida(request(),'ticker',sorteo.id,d[2].id,1,None,6,self.db)
        ticker=salida.ticker_pvw
        self.preparar_graph(sorteo,d[0]);self.assertEqual(salida.ticker_pvw,ticker)
        tv.vaciar_preview(request(),'graph',self.db);self.assertEqual(salida.graph_pgm,primero)
        tv.cambiar_aire(request(),'graph',1,None,self.db)
        self.assertFalse(json.loads(salida.graph_pgm)['visible']);self.assertEqual(salida.token,token)
        self.db.expire_all();self.assertEqual(self.db.get(TvSalida,salida.id).ticker_pvw,ticker)

    def test_tv_diseno_solo_pvw(self):
        c=self.carga(1,[1]*4);self.preparar_graph(c.sorteo,c.sorteo.detalles[0]);tv.cambiar_aire(request(),'graph',1,None,self.db)
        salida=tv.obtener_o_crear_salida(self.db);pgm=salida.graph_pgm
        asyncio.run(tv.guardar_configuracion(request('/tv/configuracion',{'tipo':'graph','graph_color_fondo':'#ABCDEF'}),self.db))
        self.assertEqual(json.loads(salida.graph_pvw)['config']['graph_color_fondo'],'#ABCDEF')
        self.assertEqual(salida.graph_pgm,pgm)
        self.preparar_graph(c.sorteo,c.sorteo.detalles[1])
        self.assertEqual(json.loads(salida.graph_pvw)['config']['graph_color_fondo'],'#ABCDEF')

    def test_limpiar_pgm_conserva_pvw_y_otras_salidas(self):
        c=self.carga(1,[1]*4)
        self.preparar_graph(c.sorteo,c.sorteo.detalles[0])
        for tipo in ['ticker','sorteo','campeonato']:
            tv.preparar_salida(request(),tipo,c.sorteo.id,None,1,'on',6,self.db)
        for tipo in tv.TIPOS_SALIDA:
            tv.cambiar_aire(request(),tipo,1,None,self.db)
        salida=tv.obtener_o_crear_salida(self.db)
        for tipo in tv.TIPOS_SALIDA:
            previews={t:getattr(salida,t+'_pvw') for t in tv.TIPOS_SALIDA}
            programas={t:getattr(salida,t+'_pgm') for t in tv.TIPOS_SALIDA}
            tv.limpiar_programa(request(),tipo,self.db)
            self.assertFalse(json.loads(getattr(salida,tipo+'_pgm'))['visible'])
            self.assertFalse(tv.al_aire(salida,tipo))
            for t in tv.TIPOS_SALIDA:
                self.assertEqual(getattr(salida,t+'_pvw'),previews[t])
                if t != tipo:self.assertEqual(getattr(salida,t+'_pgm'),programas[t])
        from fastapi import HTTPException
        req=request();req.session['usuario_rol']='LOCUCION'
        with self.assertRaises(HTTPException):tv.limpiar_programa(req,'graph',self.db)

    def test_tv_resultados_congelados(self):
        c=self.carga(1,[1]*4)
        tv.preparar_salida(request(),'campeonato',c.sorteo.id,None,1,'on',6,self.db)
        tv.cambiar_aire(request(),'campeonato',1,None,self.db)
        salida=tv.obtener_o_crear_salida(self.db);pgm=salida.campeonato_pgm
        c.detalles[0].puntos=99;self.db.commit()
        response=tv.estado_salida_vmix(salida.token,'campeonato',0,self.db)
        self.assertEqual(json.loads(response.body),json.loads(pgm))

    def test_templates(self):
        from jinja2 import Environment, FileSystemLoader
        env=Environment(loader=FileSystemLoader('app/templates'))
        for path in Path('app/templates').rglob('*.html'):
            env.parse(path.read_text(encoding='utf-8-sig'))
        self.carga(1,[1]*4)
        for tab in tv.TIPOS_SALIDA:
            response=tv.panel_tv(request(),tab,self.camp.id,self.fechas[0].id,self.cat.id,self.db)
            self.assertIn(b'MANDAR AL AIRE',response.body)

    def test_historica_simulacion_y_protecciones(self):
        from scripts import recalcular_clasificacion as script
        self.carga(1,[1,1,1,5]);self.carga(2,[0]*4)
        for j in self.jinetes:
            j.estado='descalificado';j.estado_causa='historica_sin_causa'
        self.jinetes[1].estado_causa='manual'
        for f in self.fechas[:2]:
            self.db.add(JineteFecha(jinete_id=self.jinetes[2].id,fecha_id=f.id,categoria_id=self.cat.id,estado='ausente'))
        self.db.commit()
        from sqlalchemy.orm import sessionmaker
        factory=sessionmaker(bind=self.engine)
        with patch.object(script,'SessionLocal',factory), patch('sys.argv',['recalcular']), redirect_stdout(io.StringIO()) as output:
            script.main()
        self.assertEqual(json.loads(output.getvalue())['reactivados'],[])
        self.db.expire_all();self.assertTrue(all(p.estado_clasificacion is None for p in self.pres))
        with patch.object(script,'SessionLocal',factory), patch('sys.argv',['recalcular','--aplicar','--confirmar-origen-puntos',*[str(j.id) for j in self.jinetes]]), redirect_stdout(io.StringIO()) as output:
            script.main()
        self.db.expire_all()
        self.assertEqual([j.estado for j in self.jinetes],['activo','descalificado','descalificado','descalificado'])
        self.assertEqual(json.loads(output.getvalue())['reactivados'],[self.jinetes[0].id])

    def test_tv_migracion_legacy_y_cuatro_salidas(self):
        c=self.carga(1,[1]*4)
        legacy=TvSalida(token='token-preservado',graph_sorteo_id=c.sorteo.id,detalle_id=c.sorteo.detalles[0].id,graph_al_aire=True)
        self.db.add(legacy);self.db.commit()
        salida=tv.obtener_o_crear_salida(self.db)
        self.assertTrue(json.loads(salida.graph_pgm)['visible'])
        self.assertEqual(salida.token,'token-preservado')
        for tipo in ['ticker','sorteo','campeonato']:
            pgms={t:getattr(salida,t+'_pgm') for t in tv.TIPOS_SALIDA}
            pvws={t:getattr(salida,t+'_pvw') for t in tv.TIPOS_SALIDA}
            tv.preparar_salida(request(),tipo,c.sorteo.id,None,2,'on',3,self.db)
            for t in tv.TIPOS_SALIDA:
                self.assertEqual(getattr(salida,t+'_pgm'),pgms[t])
                if t != tipo: self.assertEqual(getattr(salida,t+'_pvw'),pvws[t])
            tv.cambiar_aire(request(),tipo,1,None,self.db)
            for t in tv.TIPOS_SALIDA:
                if t != tipo:self.assertEqual(getattr(salida,t+'_pgm'),pgms[t])

    def test_http_formularios(self):
        from fastapi import FastAPI
        from urllib.parse import urlencode
        from app.core.database import get_db
        from app.routers import campeonatos,categorias,fechas
        app=FastAPI()
        for r in [tv,campeonatos,categorias,fechas,publico]:app.include_router(r.router)
        app.dependency_overrides[get_db]=lambda:self.db

        async def call(path,form=None,query=b''):
            messages=[]
            body=urlencode(form or {}).encode()
            async def receive():return {'type':'http.request','body':body,'more_body':False}
            async def send(message):messages.append(message)
            scope={'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'POST' if form is not None else 'GET','path':path,'raw_path':path.encode(),'query_string':query,'root_path':'','scheme':'http','server':('test',80),'client':('test',123),'headers':[(b'content-type',b'application/x-www-form-urlencoded')],'session':{'usuario_id':1,'usuario_rol':'MASTER'}}
            await app(scope,receive,send)
            return messages[0]['status'],b''.join(m.get('body',b'') for m in messages[1:])
        status,_=asyncio.run(call(f'/campeonatos/{self.camp.id}/editar',{'nombre':'Editado','estado':'activo','publicado':'true','informacion_publica':'Información','reglamento_publico':'Reglamento','documento_url':'https://example.com/reglamento.pdf'}))
        self.assertEqual(status,303);self.assertEqual(self.camp.reglamento_publico,'Reglamento')
        status,body=asyncio.run(call('/campeonato'));self.assertEqual(status,200);self.assertIn(b'Reglamento',body)
        status,_=asyncio.run(call(f'/fechas/{self.fechas[0].id}/editar',{'nombre':'F1','fecha':'2026-01-01','localidad':'Río Negro','estado':'programada','estado_publico_manual':'reprogramada'}))
        self.assertEqual(status,303);self.assertEqual(self.fechas[0].estado,'programada');self.assertEqual(self.fechas[0].estado_publico,'REPROGRAMADA')
        self.carga(1,[1]*4)
        for tab in tv.TIPOS_SALIDA:
            status,body=asyncio.run(call('/tv',query=f'tab={tab}'.encode()))
            self.assertEqual(status,200);self.assertIn(b'MANDAR AL AIRE',body)
        status,_=asyncio.run(call('/tv/configuracion',{'tipo':'graph','graph_color_fondo':'#010203'}));self.assertEqual(status,303)
        salida=tv.obtener_o_crear_salida(self.db)
        status,body=asyncio.run(call(f'/tv/salida/{salida.token}/graph/estado',query=b'preview=1'))
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['config']['graph_color_fondo'],'#010203')


class MigrationTest(unittest.TestCase):
    def test_head(self):
        cfg=Config();cfg.set_main_option('script_location','alembic')
        scripts=ScriptDirectory.from_config(cfg)
        self.assertEqual(scripts.get_heads(),['b38da91f7205'])
        self.assertEqual(scripts.get_revision('head').down_revision,'a27c9d8e6104')

    def test_sqlite_upgrade_downgrade(self):
        with tempfile.TemporaryDirectory() as temp:
            url='sqlite:///'+str(Path(temp)/'prueba.db').replace('\\','/')
            previous=os.environ['DATABASE_URL'];os.environ['DATABASE_URL']=url
            from app.core.config import settings
            previous_setting=settings.DATABASE_URL;settings.DATABASE_URL=url
            try:
                cfg=Config();cfg.set_main_option('script_location','alembic')
                command.upgrade(cfg,'f6b1c92e4d70')
                command.upgrade(cfg,'head')
                engine=create_engine(url)
                with engine.connect() as conn:
                    self.assertEqual(conn.scalar(text('select version_num from alembic_version')),'b38da91f7205')
                engine.dispose()
                command.downgrade(cfg,'f6b1c92e4d70')
                command.upgrade(cfg,'head')
            finally:
                os.environ['DATABASE_URL']=previous;settings.DATABASE_URL=previous_setting

    def test_postgresql_ddl(self):
        buffer=io.StringIO()
        for filename in ['a27c9d8e6104_repechaje_publico_pvw_pgm.py','b38da91f7205_repechaje_previo_f3.py']:
            spec=importlib.util.spec_from_file_location('migration','alembic/versions/'+filename)
            mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
            ctx=MigrationContext.configure(dialect_name='postgresql',opts={'as_sql':True,'output_buffer':buffer})
            with Operations.context(ctx): mod.upgrade()
        sql=buffer.getvalue()
        self.assertIn('BOOLEAN DEFAULT false NOT NULL',sql)
        self.assertIn('graph_pgm TEXT',sql)
        self.assertIn('CREATE TABLE repechajes_categorias',sql)



if __name__=='__main__': unittest.main()
