<?php
require_once 'app.php';
$date = date('Y-m-d');
$maquina = $_GET['maquina'];
$qry = "SELECT * FROM lecturas WHERE STR_TO_DATE(fecha, '%Y-%m-%d') = STR_TO_DATE('$date', '%Y-%m-%d') AND maquina = '$maquina' ORDER BY maquina, id DESC limit 50";
$data = $conn->query($qry);

echo json_encode($data->fetch_all(MYSQLI_ASSOC));
$conn->close();
?>
