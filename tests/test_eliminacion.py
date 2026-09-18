import unittest
from sqlalchemy import select, text
from fastapi import HTTPException
import test_reformas_2026 as base
from test_reformas_2026 import request
from app.models import Usuario, Jinete, Caballo, Campeonato, Fecha, Sorteo, TvSalida
from app.models.resultado import ResultadoCategoria, ResultadoDetalle
from app.models.caballo_historial import CaballoHistorial
from app.models.repechaje import RepechajeCategoria
from app.models.sorteo_auditoria import SorteoAuditoria
from app.routers import campeonatos, fechas, sorteos
import json


class EliminacionTest(unittest.TestCase):
    carga = base.ReglasTest.carga
    tearDown = base.ReglasTest.tearDown

    def setUp(self):
        base.ReglasTest.setUp(self)
        self.db.execute(text('PRAGMA foreign_keys=ON'))
        self.db.add(Usuario(id=1,nombre='Admin',usuario='prueba',password_hash='no-utilizable',rol='ADMIN'))
        self.otro=Campeonato(nombre='Conservar',estado='activo')
        self.db.add(self.otro);self.db.commit()
        c=self.carga(1,[1]*4)
        self.sid=c.sorteo_id;self.fid=self.fechas[0].id;self.cid=self.camp.id
        self.tv=TvSalida(token='preservar-url',sorteo_id=self.sid,graph_sorteo_id=self.sid,detalle_id=c.sorteo.detalles[0].id,graph_pgm='{"visible":true}')
        self.hist=CaballoHistorial(caballo_id=self.caballo.id,campeonato_id=self.cid,fecha_id=self.fid,categoria_id=self.cat.id,evento='alta')
        self.db.add_all([self.tv,self.hist,RepechajeCategoria(categoria_id=self.cat.id,base_firma='prueba',estado='borrador',puntos_json='{}')]);self.db.commit()

    def test_roles_rechazados_sin_borrar(self):
        for rol in ['SECRETARIA','LOCUCION','TV','ACREDITACION','']:
            req=request();req.session['usuario_rol']=rol
            for fn,ident in [(campeonatos.eliminar_campeonato,self.cid),(fechas.eliminar_fecha,self.fid),(sorteos.eliminar_sorteo,self.sid)]:
                with self.assertRaises(HTTPException) as error:fn(ident,req,self.db)
                self.assertEqual(error.exception.status_code,403)
        self.assertIsNotNone(self.db.get(Sorteo,self.sid))

    def comprobar_padrones(self):
        self.assertEqual(len(self.db.scalars(select(Jinete)).all()),4)
        self.assertEqual(len(self.db.scalars(select(Caballo)).all()),1)
        self.assertIsNotNone(self.db.get(Campeonato,self.otro.id))
        self.assertEqual(self.tv.token,'preservar-url')
        self.assertTrue(json.loads(self.tv.graph_pgm)['visible'])
        self.assertEqual(self.db.execute(text('PRAGMA foreign_key_check')).all(),[])

    def test_admin_borra_campeonato_real(self):
        req=request();req.session['usuario_rol']='ADMIN'
        campeonatos.eliminar_campeonato(self.cid,req,self.db)
        self.assertIsNone(self.db.get(Campeonato,self.cid))
        self.assertEqual(self.db.scalars(select(ResultadoDetalle)).all(),[])
        self.assertEqual(self.db.scalars(select(RepechajeCategoria)).all(),[])
        self.assertIsNone(self.hist.fecha_id);self.assertIsNone(self.hist.campeonato_id)
        self.comprobar_padrones()

    def test_master_borra_fecha_con_resultados(self):
        fechas.eliminar_fecha(self.fid,request(),self.db)
        self.assertIsNone(self.db.get(Fecha,self.fid))
        self.assertIsNotNone(self.db.get(Campeonato,self.cid))
        self.assertEqual(len(self.db.scalars(select(Fecha)).all()),3)
        self.assertEqual(self.db.scalars(select(ResultadoCategoria)).all(),[])
        self.comprobar_padrones()

    def test_admin_borra_sorteo_con_resultados_y_audita(self):
        req=request();req.session['usuario_rol']='ADMIN'
        sorteos.eliminar_sorteo(self.sid,req,self.db)
        self.assertIsNone(self.db.get(Sorteo,self.sid))
        self.assertIsNotNone(self.db.get(Fecha,self.fid))
        self.assertEqual(self.db.scalars(select(ResultadoDetalle)).all(),[])
        self.assertEqual(len(self.db.scalars(select(SorteoAuditoria)).all()),1)
        self.assertIsNone(self.tv.graph_sorteo_id)
        self.comprobar_padrones()
