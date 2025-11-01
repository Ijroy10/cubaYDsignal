"""
EXTENSIÓN DE USER MANAGER PARA ACCESOS NO AUTORIZADOS
Métodos adicionales para gestionar y reportar accesos no autorizados
"""

from typing import Dict, List
from datetime import datetime


def obtener_accesos_no_autorizados(user_manager, fecha: str = None, limite: int = 50) -> List[Dict]:
    """Obtiene el historial de accesos no autorizados"""
    if fecha:
        accesos = [a for a in user_manager.historial_accesos_no_autorizados 
                  if a.get('fecha_hora', '').startswith(fecha)]
    else:
        accesos = user_manager.historial_accesos_no_autorizados
    return sorted(accesos, key=lambda x: x.get('timestamp', ''), reverse=True)[:limite]


def obtener_estadisticas_accesos_no_autorizados(user_manager, fecha: str = None) -> Dict:
    """Obtiene estadísticas de accesos no autorizados"""
    accesos = obtener_accesos_no_autorizados(user_manager, fecha)
    total = len(accesos)
    por_motivo = {}
    usuarios_unicos = set()
    
    for acceso in accesos:
        motivo = acceso.get('motivo', 'desconocido')
        por_motivo[motivo] = por_motivo.get(motivo, 0) + 1
        usuarios_unicos.add(acceso.get('user_id'))
    
    return {
        'total_intentos': total,
        'usuarios_unicos': len(usuarios_unicos),
        'por_motivo': por_motivo,
        'accesos': accesos
    }


def generar_reporte_accesos_no_autorizados(user_manager, fecha: str = None, limite: int = 20) -> str:
    """Genera un reporte de accesos no autorizados"""
    stats = obtener_estadisticas_accesos_no_autorizados(user_manager, fecha)
    
    if stats['total_intentos'] == 0:
        return "🔒 **ACCESOS NO AUTORIZADOS**\n\n✅ No hay registros de accesos no autorizados."
    
    fecha_texto = f" del {fecha}" if fecha else ""
    reporte = f"🔒 **ACCESOS NO AUTORIZADOS{fecha_texto}**\n\n"
    reporte += f"**Total de intentos:** {stats['total_intentos']}\n"
    reporte += f"**Usuarios únicos:** {stats['usuarios_unicos']}\n\n"
    
    reporte += "**POR MOTIVO:**\n"
    for motivo, count in stats['por_motivo'].items():
        emoji = "🔑" if motivo == "clave_incorrecta" else "📋" if motivo == "no_autorizado" else "⚠️"
        motivo_texto = {
            'clave_incorrecta': 'Clave incorrecta',
            'no_autorizado': 'No en lista diaria',
            'no_lista_diaria': 'Sin lista diaria'
        }.get(motivo, motivo)
        reporte += f"• {emoji} {motivo_texto}: {count}\n"
    
    reporte += f"\n**ÚLTIMOS {min(limite, len(stats['accesos']))} INTENTOS:**\n"
    
    for i, acceso in enumerate(stats['accesos'][:limite], 1):
        motivo = acceso.get('motivo', 'desconocido')
        emoji = "🔑" if motivo == "clave_incorrecta" else "📋"
        
        reporte += f"\n**{i}.** {emoji} @{acceso.get('username', 'Sin username')}\n"
        reporte += f"• **ID:** `{acceso.get('user_id')}`\n"
        reporte += f"• **Motivo:** {motivo}\n"
        if acceso.get('clave_usada'):
            reporte += f"• **Clave usada:** `{acceso.get('clave_usada')}`\n"
        reporte += f"• **Fecha:** {acceso.get('fecha_hora')}\n"
    
    return reporte
