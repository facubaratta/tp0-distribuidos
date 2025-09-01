# TP0: Docker + Comunicaciones + Concurrencia

Facundo Baratta - 104886

## Parte 1: Introducción a Docker

### Ejercicio N°1:

Como es sugerido en la solución, `generar-compose.sh` llama a un script de python (creativamente llamado) `generar-compose.py`. El script de bash recibe dos parametros: nombre del archivo de entrada, y de salida. Estos son pasados al script de python. Si la cantidad de variables de entrada es distinta de dos, se muestra ayuda de uso.
El script de python genera un archivo docker-compose con estructura similar al suministrado en el repositorio inicialmente.

### Ejercicio N°2:

Para este ejercicio se montó los archivos de configuración para el servidor y cada cliente respectivamente. Luego, se eliminó las variables de entorno generadas para el .yml para que no pisen a lo seteado en la configuración. Finalmente, se eliminó copiar el archivo de configuración en el Dockerfile. No es necesario ya que se monta como volumen.

### Ejercicio N°3:

El creado script primero genera un string con timestamp único. Luego levanta un contenedor efimero ligero, el cual se conecta a la red de Docker. Con nc se abre un socket TCP al cual se le manda el string, el cual se espera que sea haga un echo idéntico, validando que la red esta saludable.

### Ejercicio N°4:

Para el cliente decidí implementar el código de manejo de señales en `main.go`. Aquí se crea un canal de señales que se subcribe a la señal SIGTERM. Este canal se lo paso como variable la función `StartClientLoop`, la cual, si hay SIGTERM, crea el log correspondiente y sale de la función, volviendo a main, y finalmente cierra el programa gracefully naturalmente. En ramas posteriores utilizaré una forma más idiomática de corroborar si hay una señal en el canal (mi primera vez programando en Go).
Similarmente para el servidor en `main.py` se subscribe la señal SIGTERM a una función `graceful_shutdown`. Esta llama a la correspondiente función de mismo nombre del servidor (variable global) - si es que existe, sino corta ejecución del programa. En `server.py` la función `graceful_shutdown` cambia el flag que permite seguir recibiendo solicitudes entrantes, e intenta cerrar el socket del servidor y todas las conexiones con los clientes, manejando y logeando los errores que puedan ocurrir.

## Parte 2: Repaso de Comunicaciones

### Ejercicio N°5:

Este ejercicio tal vez tenga la mayor cantidad de código ya que hay que definir el protocolo (inicialmente usé JSON 😿) y toda la lógica de negocio.
En `domain.go` se copia la estructura de apuesta definida en `utils.py` en el servidor y se agrega una funcion que lo parsea de las variable de entorno (que se agregaron al `generar-compose.py` como dummy). Se inicializa con ese helper en `main.go` y se pasa como variable a la función `StartClientLoop`.
`server.py` se modificó para utilizar la lógica de negocio. Se lee la apuesta, se guarda utilizando la función de `utils.py` y se manda un ACK. Se cierra la conexión luego de una única apuesta.

Es en `transfer.go` y `transfer.py` donde se aprecia el protocolo implementando. No es TLV ya que no hay type por campo, pero el Type está implícito en el magic del mensaje y el orden fijo de los campos.
El header son 4 bytes big endian que indican la longitud del payload. Se espera leer o escribir esa longitud luego de leer o escribir esos 4 bytes. De esta forma, evito errores de short read/write.
Luego, se manda un "MAGIC" string de también 4 bytes que indica el tipo de mensaje. Aquí, es BET0 o ACK0.

El formato BET es el siguiente:

```
"BET0"
[agency: u16 BE]
[first_name: u16 len][bytes...]
[last_name : u16 len][bytes...]
[document : u16 len][bytes...]
[birthdate : 10 bytes ASCII "YYYY-MM-DD"]
[number : u32 BE]
```

Y el del ACK:

```
"ACK0"
[ok: 1 byte 0|1]
[si ok==0 => error: u16 len + bytes]
```

### Ejercicio N°6:

En `transfer.go/.py` cambié el protocolo. Ahora el header es BCH0 o ACK0. En el caso de un batch, luego del header, 2 bytes big endian con la cantidad de batches. Luego, cada batch serializado como en el ejercicio anterior, uno detrás del otro, pero con un header de longitud para cada uno.
El ACK cambia: luego del magic, un bit de ok como anteriormente, pero luego dos bytes de cantidad recibida (aunque en caso de un error esto es 0, lo que puede suceder es que no se detecte error desde el servidor pero el cliente verifica que la cantidad es la enviada).

Se eliminó las variables de entorno del script generador de docker compose, y ahora se monta el archivo correspondiente como otro volumen.

Inicialmente cargaba todo el archivo en memoria pero lo cambié 😿

Empezando por `domain.go`, la función helper que cargaba una apuesta desde las variables de entorno es reemplazada por un iterador que permite ir leyendo apuestas de una manera ya parseada y completamente abstraída. Este iterador es inicializado en `main.go` y se pasa a `StartClientLoop` como una variable junto con `batchMax` y `maxBytes`.
En el loop del cliente envia los batches iterando secuencialmente. También tiene un `pending` habilitado en caso de que el batch supere los maxBytes (8kb). Esto se chequea dinámicamente, lo cual es un poco [overkill](https://i.imgflip.com/2q9wdh.jpg?a487704) tal vez.

### Ejercicio N°7:

## Parte 3: Repaso de Concurrencia

En este ejercicio es importante considerar los mecanismos de sincronización a utilizar para el correcto funcionamiento de la persistencia.

### Ejercicio N°8:

Modificar el servidor para que permita aceptar conexiones y procesar mensajes en paralelo. En caso de que el alumno implemente el servidor en Python utilizando _multithreading_, deberán tenerse en cuenta las [limitaciones propias del lenguaje](https://wiki.python.org/moin/GlobalInterpreterLock).

## Condiciones de Entrega

Se espera que los alumnos realicen un _fork_ del presente repositorio para el desarrollo de los ejercicios y que aprovechen el esqueleto provisto tanto (o tan poco) como consideren necesario.

Cada ejercicio deberá resolverse en una rama independiente con nombres siguiendo el formato `ej${Nro de ejercicio}`. Se permite agregar commits en cualquier órden, así como crear una rama a partir de otra, pero al momento de la entrega deberán existir 8 ramas llamadas: ej1, ej2, ..., ej7, ej8.
(hint: verificar listado de ramas y últimos commits con `git ls-remote`)

Se espera que se redacte una sección del README en donde se indique cómo ejecutar cada ejercicio y se detallen los aspectos más importantes de la solución provista, como ser el protocolo de comunicación implementado (Parte 2) y los mecanismos de sincronización utilizados (Parte 3).

Se proveen [pruebas automáticas](https://github.com/7574-sistemas-distribuidos/tp0-tests) de caja negra. Se exige que la resolución de los ejercicios pase tales pruebas, o en su defecto que las discrepancias sean justificadas y discutidas con los docentes antes del día de la entrega. El incumplimiento de las pruebas es condición de desaprobación, pero su cumplimiento no es suficiente para la aprobación. Respetar las entradas de log planteadas en los ejercicios, pues son las que se chequean en cada uno de los tests.

La corrección personal tendrá en cuenta la calidad del código entregado y casos de error posibles, se manifiesten o no durante la ejecución del trabajo práctico. Se pide a los alumnos leer atentamente y **tener en cuenta** los criterios de corrección informados [en el campus](https://campusgrado.fi.uba.ar/mod/page/view.php?id=73393).
