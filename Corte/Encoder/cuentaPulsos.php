<?php
require_once 'app.php';

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $valor = $_POST['valor'];
    $estado = $_POST['estado'];
    $maquina = $_POST['maquina'];

  $fecha = date('Y-m-d H:i:s');
        
    $sql = "INSERT INTO lecturas (valor, estado,maquina,fecha) VALUES ($valor, '$estado','$maquina','$fecha')";

    if ($conn->query($sql) === TRUE) {
        echo "Registro guardado con éxito";
    } else {
        echo "Error: " . $sql . "<br>" . $conn->error;
    
    }
   
}
$conn->close();
?>