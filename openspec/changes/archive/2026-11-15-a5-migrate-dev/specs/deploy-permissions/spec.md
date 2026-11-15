# Spec Delta

## Purpose

Define las identidades con las que CI despliega cada entorno y con las que la API se ejecuta, y los límites que impiden que un entorno afecte a otro o exceda sus permisos.

## ADDED Requirements

### Requirement: Retiro de permisos heredados
Cuando ningún entorno conserve recursos de Lambda o API Gateway, los roles de despliegue y el límite de permisos MUST NOT incluir acciones de esos servicios.

#### Scenario: Bootstrap tras la migración
- **WHEN** se inspeccionan las políticas de los roles de despliegue después de migrar `dev`
- **THEN** no contienen acciones `lambda:*` ni `apigateway:*`

#### Scenario: Despliegue posterior
- **WHEN** se despliega `dev` o un preview después del retiro
- **THEN** el despliegue se completa sin errores de acceso
