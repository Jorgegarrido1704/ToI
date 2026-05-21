<?php
$servidor = "localhost";
$usuario  = "root";
$password = "";
$dbname   = "toi";

$conn = new mysqli($servidor, $usuario, $password, $dbname);

if ($conn->connect_error) {
    die("Conexión fallida: " . $conn->connect_error);
}
date_default_timezone_set('America/Mexico_City');