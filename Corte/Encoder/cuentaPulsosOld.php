<?php
require_once 'app.php';

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $valor = $_POST['valor'];
    $estado = $_POST['estado'];
    $maquina = $_POST['maquina'];

    $last= "SELECT estado FROM lecturas ORDER BY id DESC LIMIT 1";    
    $restultimpo = $conn->query($last);

    if ($restultimpo->num_rows > 0) {
        while($row = $restultimpo->fetch_assoc()) {
            $ultimoEstado = $row["estado"];
        }
    }
    if($estado !=$ultimoEstado){
        
   $sql = "INSERT INTO lecturas (valor, estado,maquina) VALUES ($valor, '$estado','$maquina')";

    if ($conn->query($sql) === TRUE) {
        echo "Registro guardado con éxito";
    } else {
        echo "Error: " . $sql . "<br>" . $conn->error;
    }
    }
   
}
$conn->close();
?>