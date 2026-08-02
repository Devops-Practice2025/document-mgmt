resource "aws_instance" "frontend" {
  ami                    = var.rhel_ami
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public-subnet.id

  vpc_security_group_ids = [aws_security_group.frontend_sg.id]

  tags = { Name = "${var.project}-frontend" }
}

resource "aws_instance" "backend" {
  ami                    = var.rhel_ami
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public-subnet.id

  vpc_security_group_ids = [aws_security_group.backend_sg.id]

  tags = { Name = "${var.project}-backend" }
}

resource "aws_instance" "mysql" {
  ami                    = var.rhel_ami
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public-subnet.id

  vpc_security_group_ids = [aws_security_group.mysql_sg.id]

  tags = { Name = "${var.project}-mysql" }
}

output "frontend_public_ip" {
  value = aws_instance.frontend.public_ip
}

output "backend_public_ip" {
  value = aws_instance.backend.public_ip
}

output "mysql_public_ip" {
  value = aws_instance.mysql.public_ip
}