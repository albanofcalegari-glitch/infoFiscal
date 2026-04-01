// JavaScript para la búsqueda de clientes
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const loadingDiv = document.getElementById('loading');
    const resultadosSection = document.getElementById('resultados');
    const clientesList = document.getElementById('clientesList');
    const busquedaInput = document.getElementById('busqueda');

    // Auto-focus en el input
    if (busquedaInput) {
        busquedaInput.focus();
    }

    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const busqueda = busquedaInput.value.trim();
            if (!busqueda) {
                alert('Por favor ingrese un término de búsqueda');
                return;
            }

            console.log('Iniciando búsqueda para:', busqueda);

            // Deshabilitar el botón y el input durante la búsqueda
            const submitButton = searchForm.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.style.opacity = '0.6';
                submitButton.style.cursor = 'not-allowed';
                submitButton.textContent = '⏳ Buscando...';
            }
            if (busquedaInput) {
                busquedaInput.disabled = true;
                busquedaInput.style.opacity = '0.6';
            }

            // Mostrar loading y ocultar resultados
            if (loadingDiv) {
                loadingDiv.style.display = 'block';
            }
            if (resultadosSection) {
                resultadosSection.style.display = 'none';
            }
            
            // Crear FormData
            const formData = new FormData();
            formData.append('busqueda', busqueda);
            
            // Hacer la petición
            fetch('/buscar-cliente', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                console.log('Respuesta recibida:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Datos recibidos:', data);

                // Re-habilitar botón e input
                const submitButton = searchForm.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.style.opacity = '1';
                    submitButton.style.cursor = 'pointer';
                    submitButton.textContent = '🔍 Buscar Cliente';
                }
                if (busquedaInput) {
                    busquedaInput.disabled = false;
                    busquedaInput.style.opacity = '1';
                }

                // Ocultar loading
                if (loadingDiv) {
                    loadingDiv.style.display = 'none';
                }

                if (data.clientes && data.clientes.length > 0) {
                    console.log('Mostrando clientes:', data.clientes.length);
                    mostrarClientes(data.clientes);
                } else {
                    console.log('No se encontraron clientes');
                    mostrarMensaje('No se encontraron clientes con ese criterio', 'warning');
                }
            })
            .catch(error => {
                console.error('Error en la búsqueda:', error);

                // Re-habilitar botón e input
                const submitButton = searchForm.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.style.opacity = '1';
                    submitButton.style.cursor = 'pointer';
                    submitButton.textContent = '🔍 Buscar Cliente';
                }
                if (busquedaInput) {
                    busquedaInput.disabled = false;
                    busquedaInput.style.opacity = '1';
                }

                // Ocultar loading
                if (loadingDiv) {
                    loadingDiv.style.display = 'none';
                }

                mostrarMensaje('Error al buscar clientes. Intente nuevamente.', 'warning');
            });
        });
    }

    function mostrarClientes(clientes) {
        if (!clientesList || !resultadosSection) return;
        
        console.log('Creando cards para', clientes.length, 'clientes');
        
        clientesList.innerHTML = '';
        
        clientes.forEach(cliente => {
            const card = document.createElement('div');
            card.className = 'client-card';
            card.onclick = () => seleccionarCliente(cliente);
            
            card.innerHTML = `
                <div class="client-name">
                    👤 ${cliente.apellido}, ${cliente.nombres}
                </div>
                <div class="client-details">
                    <div><strong>📄 CUIT:</strong> ${cliente.CUIT || 'N/A'}</div>
                    <div><strong>🆔 DNI:</strong> ${cliente.nroDocumento || 'N/A'}</div>
                    <div><strong>🏢 IVA:</strong> ${cliente.condicionIVA || 'N/A'}</div>
                </div>
            `;
            
            clientesList.appendChild(card);
        });
        
        resultadosSection.style.display = 'block';
        console.log('Resultados mostrados');
    }
    
    function mostrarMensaje(mensaje, tipo) {
        if (!clientesList || !resultadosSection) return;
        
        console.log('Mostrando mensaje:', mensaje);
        
        const alertClass = tipo === 'warning' ? 'alert-warning' : 'alert-info';
        
        clientesList.innerHTML = `
            <div class="alert ${alertClass}">
                ⚠️ ${mensaje}
            </div>
        `;
        
        resultadosSection.style.display = 'block';
    }
    
    function seleccionarCliente(cliente) {
        console.log('Cliente seleccionado:', cliente);

        // Deshabilitar el formulario de búsqueda
        const submitButton = searchForm.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.style.opacity = '0.5';
            submitButton.style.cursor = 'not-allowed';
            submitButton.textContent = '⏳ Consultando AFIP...';
        }
        if (busquedaInput) {
            busquedaInput.disabled = true;
            busquedaInput.style.opacity = '0.5';
        }

        // Efecto visual en la tarjeta
        const card = event.currentTarget;
        card.style.background = 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)';
        card.style.borderColor = '#2563eb';
        card.style.pointerEvents = 'none'; // Deshabilitar clicks adicionales

        // Agregar texto de carga
        const loadingText = document.createElement('div');
        loadingText.style.cssText = 'margin-top: 10px; color: #2563eb; font-weight: bold; text-align: center;';
        loadingText.innerHTML = '⏳ Buscando facturas AFIP...';
        card.appendChild(loadingText);

        // Deshabilitar todas las otras tarjetas
        const allCards = document.querySelectorAll('.client-card');
        allCards.forEach(c => {
            if (c !== card) {
                c.style.opacity = '0.5';
                c.style.pointerEvents = 'none';
            }
        });

        // Redirigir después de un momento
        setTimeout(() => {
            window.location.href = `/consultar-facturas-unificada?cliente_id=${cliente.id}`;
        }, 500);
    }
});

console.log('JavaScript de búsqueda cargado correctamente');