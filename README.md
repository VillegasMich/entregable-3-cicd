- Repo: https://github.com/VillegasMich/entregable-3-cicd
- Sonar: https://sonarcloud.io/project/overview?id=VillegasMich_entregable-3-cicd
- Imagen: villegasmich/entregable-3-cicd


- ALB URL Staging: http://calculadora-staging-alb-462007611.us-east-1.elb.amazonaws.com/
- ALB URL Production: http://calculadora-production-alb-480919015.us-east-1.elb.amazonaws.com/


1. Explica brevemente el flujo de trabajo nuevo completo que implementaste con Terraform (commit -> CI -> Build/Push Imagen -> Deploy TF Staging -> Update Service Staging -> Test Staging -> Deploy TF Prod -> Update Service Prod -> Smoke Test Prod). Sé específico sobre qué artefacto se mueve, qué hace cada job principal, y qué valida cada tipo de prueba.

Tenemos que el flujo arranca con un push al main. Aquí se ejecuta el job de CI "build-test-publish" que lo que hace básicamente es correr las pruebas unitarias y los análisis estáticos de código con flake8, Pylint… Una vez todo lo anterior pasa ok, se hace build y se publica la imagen de Docker etiquetada con el SHA. El artefacto en este caso seria esa imagen de Docker que queda en DockerHub con su tag.

Después encontramos el job de deploy-tf-staging el cual se encarga de configurar las credenciales de AWS con los Github Secrets. Luego viene el Terraform init que apunta al estado remoto en S3. Lo anterior lo que hace es actualizar los recursos de infraestructura del entorno de Staging en AWS (cluste ECS, el ALB, los Security Groups, etc.), es decir, Terraform al detectar cualquier diferencia, aplica solo los cambios necesarios.

Continuamos con el update-service-staging que se encarga de ejecutar `aws ecs update-service --force-new-deployment` que básicamente descarga la imagen nueva y lanza los contenedores, después de esto, se espera hasta que el servicio sea estable.

Ahora que se tiene el servicio de Staging corriendo, entra el job acceptance-test-Staging que lo que hace es ejecutar las pruebas de aceptación apuntando al ALB usando la variable APP_BASE_URL que configuramos en nuestro código. Lo que hacen estas pruebas es que validan flujos completos "de cara al usuario" con Selenium, en este caso que la calculadora sume, reste, multiplique, divida y además que realice las operaciones de potencia y modulo las cuales agregamos.

Cuando las pruebas de Staging se ejecutan ok, continua nuestro pipeline con deploy-tf-prod, el cual se realiza igualmente con Terraform pero inicializado con la key `production/terraform.tfstate`. De esta forma, actualiza la infra de producción para que después, venga el update-service-prod y se realiza el despliegue en producción y como paso anteriormente, esperar a que se estabilice.

Para terminar, smoke-test-prod ejecuta las pruebas en `test_smoke_app.py` apuntando al ALB de producción. Estas en general son pruebas simples, su principal objetivo es encargarse de verificar que la pagina principal cargue, es decir, confirman que la aplicación este viva y corriendo adecuadamente.

---

2. ¿Qué ventajas y desventajas encontraste al usar Terraform o infraestructura como código en vez de desplegar manualmente? ¿Qué te pareció definir la infraestructura en HCL?

La ventaja mas grande que encontramos es la consistencia. En este caso tenemos dos entornos los cuales parten del mismo "molde" o plantilla por así decirlo, simplemente cambia el nombre del ambiente. Digamos que si creamos manualmente los recursos en la consola de AWS probablemente entre Staging y Produccion vayamos a tener configuraciones ligeramente distintas de las cuales tal vez ni siquiera lleguemos a darnos cuenta, mientras que utilizando IaC con Terraform sentimos cierta tranquilidad de que esto no pasara.

Otra ventaja que creemos que es importante mencionar, es la capacidad de reproducir el despliegue mas de una vez, ya que simplemente corriendo el `terraform apply` se crea todo nueva y exactamente igual, en caso de haberlo hecho de forma manual, deberíamos estar recordando que configuramos anteriormente.

Como desventaja, la curva de aprendizaje de HCL fue real, especialmente entender data sources, dependencias implícitas y manejar el formato de variables como la lista de subnets. Además, `terraform apply` alarga bastante el pipeline porque crear un ALB y un cluster ECS toma varios minutos.

---

3. ¿Qué ventajas y desventajas tiene introducir un entorno de Staging en el pipeline de despliegue a AWS? ¿Cómo impacta esto la velocidad vs. la seguridad del despliegue?

La principal ventaja es que digamos que tenemos una capa más que actúa como un filtro o red de seguridad, ya que por ejemplo si la imagen tiene algún error o bug que pudo llegar a pasar los test existentes, las pruebas de aceptación lo van a detectar antes de que llegue a los usuarios reales en producción y les genere afectaciones reales que pueden generar gran impacto en la empresa. También permite probar cambios de infraestructura con menor riesgo.

Una desventaja real que vemos es que se nos duplican costos ya que debemos mantener más recursos de AWS y el pipeline en general tarda más, pero esta tardanza en realidad no es mala, ya que en el futuro se va a reflejar que es mejor tomar un poco mas tiempo antes de salir a producción a cambio de mayor confianza. Si se sale rápido a producción, pero sin realizar las verificaciones adecuadas con el objetivo de ahorrar tiempo, quedaremos con una deuda técnica que va creciendo como una bola de nieve que en el futuro nos va a llevar muchísimo mas tiempo del que nos hubiese tomado realizar el proceso completo desde el inicio.

---

4. ¿Qué diferencia hay entre las pruebas ejecutadas contra Staging (test-staging) y las ejecutadas contra Producción (smoke-test-production) en tu pipeline? ¿Por qué esta diferencia?

Las pruebas de Staging son pruebas de aceptación con Selenium, estas buscan simular un usuario real llenando el formulario y verificando resultados de todas las operaciones. Son mucho más exhaustivas.

Los smoke tests de Producción solo verifican que la app esté viva, que la página principal responda y tenga el título correcto. Son mínimos pero rápidos.

La diferencia es de propósito, en Staging queremos máxima cobertura funcional porque es el filtro de calidad que mencionamos anteriormente. En Producción solo queremos confirmar que el despliegue no rompió nada grave, y si falla hay que hacer rollback de inmediato.

---

5. Considerando un ciclo completo de DevOps, ¿qué partes importantes (fases, herramientas, prácticas) crees que aún le faltan a este pipeline de CI/CD que has construido? (Menciona 2, explica por qué son importantes y cómo podrían implementarse brevemente).

Podríamos implementar:

- **Estrategia de despliegue avanzada como Blue/Green o Canary:** el pipeline actual hace un rolling update básico, lo que significa que si hay un bug crítico ya está afectando usuarios antes de que los smoke tests lo detecten. Con un despliegue como por ejemplo Blue/Green, el nuevo entorno estaría listo antes de cambiar el tráfico y el rollback sería instantáneo.

- **Un Rollback automatizado:** por ejemplo, si los smoke tests de Producción fallan, el pipeline simplemente falla pero no revierte nada. Se podría agregar un job con `if: failure()` que restaure automáticamente la task definition anterior en ECS, cerrando así el ciclo de seguridad del CD.

---

6. ¿Cómo te pareció implementar dos funcionalidades nuevas? ¿Qué tal fue tu experiencia? ¿Encontraste útil implementar CI/CD a la hora de realizar cambios y despliegues? ¿Por qué? ¿Qué no fue tan útil?

Agregar las operaciones de potencia y módulo fue algo sencillo en términos de código. Lo que realmente consideramos valioso es que el pipeline nos genera confianza para hacer el cambio (ya que como lo mencionamos anteriormente, ya tenemos un molde que nos garantiza que los cambios que realizamos van a pasar por las comprobaciones y pasos necesarios antes de estar disponibles de cara al usuario). Una vez se hace el push, en minutos podemos ver todos los jobs en verde, con los tests validando que nada se rompió.

Lo menos útil fue el tiempo de espera cada push tardaba 8-10 minutos por los despliegues de Terraform y las esperas de ECS. Para iteraciones rápidas ese ciclo de feedback se siente largo, aunque es un trade-off aceptable dado lo que garantiza.

Digamos que si no usamos estos flujos de CI/CD, cada que realizamos un cambio por mínimo que sea, siempre queda esa duda de "¿será que rompí algo en otro lado?", pero el implementar los pipelines con las pruebas necesarias quita esa duda y la convierte en seguridad. Digamos que al inicio puede ser algo tedioso toda la implementación o entendimiento de los pasos que se llevan a cabo, pero es un tiempo necesario al inicio que nos ahorrara muchos dolores de cabeza a futuro.