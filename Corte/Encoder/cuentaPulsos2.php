<?php
$servidor = "localhost";
$usuario  = "root";
$password = "";
$dbname   = "tiemposmaqinas";

$conn = new mysqli($servidor, $usuario, $password, $dbname);

if ($conn->connect_error) {
    die("Conexión fallida: " . $conn->connect_error);
}
date_default_timezone_set('America/Mexico_City');

if ($_SERVER["REQUEST_METHOD"] == "POST") {
   $valor = $_POST['valor'];
    $estado = $_POST['estado'];
    $maquina = $_POST['maquina'];

  $diashoras= date('Y-m-d H:i:s');
    $buscarLast= "SELECT * FROM `tiemposmaqinas` WHERE maquina = '$maquina' ORDER BY id DESC LIMIT 1";
    $restultimpo = $conn->query($buscarLast);

    if ($restultimpo->num_rows > 0) {
        while($row = $restultimpo->fetch_assoc()) {
            $ultimoEstado = $row["inicioEstatdo"];
            $ultimoTiempo = $row["inicioTiempoEstado"];
            $tiempo = time() - strtotime($ultimoTiempo);
            $tiempo = $tiempo / 60;
            $update = "UPDATE `tiemposmaqinas` SET `finEstado` = '$ultimoEstado', `finTiempoEstado` = '$diashoras', `tiempoEnMinutos` = '$tiempo' WHERE maquina = '$maquina' ORDER BY id DESC LIMIT 1";
            $conn->query($update);
        }
    }
   
        
   
   $sql = "INSERT INTO `tiemposmaqinas`( `maquina`, `inicioEstatdo`, `inicioTiempoEstado`) VALUES ('$maquina','$estado','$diashoras')";

    if ($conn->query($sql) === TRUE) {
        echo "Registro guardado con éxito";
    } else {
        echo "Error: " . $sql . "<br>" . $conn->error;
    
    }
   
}
$conn->close();
?>