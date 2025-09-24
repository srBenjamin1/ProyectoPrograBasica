REQUISITO = 5

alumnos = []
lugares = []
registros = []

def nuevo_id(lista):
    mayor = 0
    for item in lista:
        if "id" in item and item["id"] > mayor:
            mayor = item["id"]
    return mayor + 1

def ver_alumnos():
    print("\n--- Alumnos ---")
    if alumnos == []:
        print("No hay alumnos.")
    else:
        for a in alumnos:
            if "id" in a and "nombre" in a and "carrera" in a:
                print("ID", a["id"], "|", a["nombre"], "|", a["carrera"])

def ver_lugares():
    print("\n--- Lugares ---")
    if lugares == []:
        print("No hay lugares.")
    else:
        for l in lugares:
            if "id" in l and "nombre" in l:
                print("ID", l["id"], "|", l["nombre"])

def agregar_alumno():
    print("\n=== Agregar alumno ===")
    nombre = input("Nombre: ").strip()
    carrera = input("Carrera: ").strip()
    if nombre == "" or carrera == "":
        print("Datos vacíos.")
    else:
        nuevo = {"id": nuevo_id(alumnos), "nombre": nombre, "carrera": carrera}
        alumnos.append(nuevo)
        print("Alumno agregado con ID:", nuevo["id"])

def agregar_lugar():
    print("\n=== Agregar lugar ===")
    nombre = input("Nombre: ").strip()
    if nombre == "":
        print("Vacío.")
    else:
        nuevo = {"id": nuevo_id(lugares), "nombre": nombre}
        lugares.append(nuevo)
        print("Lugar agregado con ID:", nuevo["id"])

def buscar(lista, el_id):
    for item in lista:
        if "id" in item and item["id"] == el_id:
            return item
    return {}

def pos(lista, el_id):
    i = 0
    for item in lista:
        if "id" in item and item["id"] == el_id:
            return i
        i = i + 1
    return -1

def agregar_registro():
    print("\n=== Agregar registro ===")
    ver_alumnos()
    s = input("ID alumno: ").strip()
    if s.isdigit():
        alumno_id = int(s)
    else:
        print("ID inválido.")
        return

    ver_lugares()
    s = input("ID lugar: ").strip()
    if s.isdigit():
        lugar_id = int(s)
    else:
        print("ID inválido.")
        return

    act = input("Actividad: ").strip()
    fecha = input("Fecha: ").strip()

    s = input("Horas: ").strip()
    if s.replace(".","",1).isdigit():
        horas = float(s)
    else:
        print("Horas inválidas.")
        return

    s = input("Semestre: ").strip()
    if s.isdigit():
        sem = int(s)
    else:
        print("Semestre inválido.")
        return

    nuevo = {
        "id": nuevo_id(registros),
        "alumno_id": alumno_id,
        "lugar_id": lugar_id,
        "actividad": act,
        "fecha": fecha,
        "horas": horas,
        "semestre": sem,
        "validado": False,
        "validador": ""
    }
    registros.append(nuevo)
    print("Registro agregado (pendiente).")

def ver_pendientes():
    print("\n--- Pendientes ---")
    hay = False
    for r in registros:
        if "validado" in r and r["validado"] == False:
            a = buscar(alumnos, r["alumno_id"])
            l = buscar(lugares, r["lugar_id"])
            if "nombre" in a:
                nombre = a["nombre"]
            else:
                nombre = "?"
            if "nombre" in l:
                lugar = l["nombre"]
            else:
                lugar = "?"
            print("ID=", r["id"], "| Alumno=", nombre, "| Lugar=", lugar,
                  "|", r["actividad"], "|", r["fecha"], "|", r["horas"],
                  "h | Sem", r["semestre"])
            hay = True
    if hay == False:
        print("No hay pendientes.")

def validar():
    print("\n=== Validar ===")
    ver_pendientes()
    s = input("ID registro: ").strip()
    if s.isdigit():
        rid = int(s)
    else:
        print("Inválido.")
        return
    p = pos(registros, rid)
    if p == -1:
        print("No existe.")
    else:
        val = input("Validador: ").strip()
        registros[p]["validado"] = True
        registros[p]["validador"] = val
        print("Validado.")

def sumar(alumno_id, sem, solo_val):
    total = 0.0
    for r in registros:
        if r["alumno_id"] == alumno_id and r["semestre"] == sem:
            if (solo_val and r["validado"]==True) or (solo_val==False):
                total = total + r["horas"]
    return total

def ver_estado():
    print("\n=== Estado ===")
    ver_alumnos()
    s = input("ID alumno: ").strip()
    if s.isdigit():
        alumno_id = int(s)
    else:
        print("ID inválido.")
        return

    s = input("Semestre: ").strip()
    if s.isdigit():
        sem = int(s)
    else:
        print("Inválido.")
        return

    todas = sumar(alumno_id, sem, False)
    ok = sumar(alumno_id, sem, True)
    falta = REQUISITO - ok
    if falta < 0:
        falta = 0

    a = buscar(alumnos, alumno_id)
    if "nombre" in a:
        nombre = a["nombre"]
    else:
        nombre = "?"
    if "carrera" in a:
        carrera = a["carrera"]
    else:
        carrera = "?"

    print("Alumno:", nombre)
    print("Carrera:", carrera)
    print("Horas todas:", todas)
    print("Horas validadas:", ok)
    print("Faltan:", falta)

def menu():
    print("\n--- MENU ---")
    print("1) Agregar alumno")
    print("2) Agregar lugar")
    print("3) Agregar registro")
    print("4) Validar")
    print("5) Ver estado")
    print("6) Ver pendientes")
    print("7) Ver alumnos")
    print("8) Ver lugares")
    print("0) Salir")

def main():
    op = "-1"
    while op != "0":
        menu()
        op = input("Opción: ").strip()
        if op == "1":
            agregar_alumno()
        elif op == "2":
            agregar_lugar()
        elif op == "3":
            agregar_registro()
        elif op == "4":
            validar()
        elif op == "5":
            ver_estado()
        elif op == "6":
            ver_pendientes()
        elif op == "7":
            ver_alumnos()
        elif op == "8":
            ver_lugares()
        elif op == "0":
            print("Adiós.")
        else:
            print("Inválido.")

if __name__ == "__main__":
    main()