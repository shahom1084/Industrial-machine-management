document.addEventListener('DOMContentLoaded', function() {
    // Form elements
    const usageForm = document.getElementById('usageForm');
    const errorForm = document.getElementById('errorForm');
    const machineSelect = document.getElementById('machineSelect');
    const statsContainer = document.getElementById('statsContainer');

    // Populate machine select with available machines
    function populateMachineSelect(machines) {
        machineSelect.innerHTML = '<option value="">Select a machine</option>';
        machines.forEach(machine => {
            const option = document.createElement('option');
            option.value = machine.machine_id;
            option.textContent = `${machine.machine_name} (${machine.type})`;
            machineSelect.appendChild(option);
        });
    }

    // Handle machine usage form submission
    usageForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {
            machine_id: machineSelect.value,
            purpose: document.getElementById('purpose').value,
            stage: document.getElementById('stage').value,
            units: document.getElementById('units').value,
            unit_type: document.getElementById('unitType').value
        };

        try {
            const response = await fetch('/submit_usage', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();
            if (result.error) {
                throw new Error(result.error);
            }
            showNotification('Usage data submitted successfully!', 'success');
            usageForm.reset();
            updateMachineStats(formData.machine_id);
        } catch (error) {
            showNotification('Error submitting usage data: ' + error.message, 'error');
            console.error('Error:', error);
        }
    });

    // Handle error report form submission
    errorForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {
            machine_id: document.getElementById('errorMachine').value,
            error_type: document.getElementById('errorType').value,
            description: document.getElementById('errorDescription').value
        };

        try {
            const response = await fetch('/report_error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();
            if (result.error) {
                throw new Error(result.error);
            }
            showNotification('Error reported successfully!', 'success');
            errorForm.reset();
            updateMachineStats(formData.machine_id);
        } catch (error) {
            showNotification('Error reporting issue: ' + error.message, 'error');
            console.error('Error:', error);
        }
    });

    // Update machine statistics when machine is selected
    machineSelect.addEventListener('change', function() {
        if (this.value) {
            updateMachineStats(this.value);
        } else {
            statsContainer.innerHTML = '<p class="placeholder">Select a machine to view its statistics</p>';
        }
    });

    // Function to update machine statistics
    async function updateMachineStats(machineId) {
        try {
            const response = await fetch(`/get_machine_stats/${machineId}`);
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            const { usage_stats, error_stats } = data;
            
            if (usage_stats.length === 0 && error_stats.length === 0) {
                statsContainer.innerHTML = '<p class="placeholder">No data available for this machine</p>';
                return;
            }

            // Calculate total units produced
            const totalUnits = usage_stats.reduce((sum, record) => sum + parseFloat(record.units), 0);
            const unitType = usage_stats[0]?.unit_type || 'units';

            // Create statistics display
            const statsHTML = `
                <div class="stats-summary fade-in">
                    <h3>Usage Summary</h3>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-label">Total Units Produced</span>
                            <span class="stat-value">${totalUnits} ${unitType}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Total Usage Records</span>
                            <span class="stat-value">${usage_stats.length}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Total Error Reports</span>
                            <span class="stat-value">${error_stats.length}</span>
                        </div>
                    </div>
                    
                    <div class="recent-activity">
                        <h3>Recent Usage Activity</h3>
                        <ul>
                            ${usage_stats.slice(-3).reverse().map(record => `
                                <li>
                                    <span class="activity-date">${new Date(record.timestamp).toLocaleString()}</span>
                                    <span class="activity-details">${record.purpose} - ${record.units} ${record.unit_type}</span>
                                </li>
                            `).join('')}
                        </ul>
                    </div>

                    ${error_stats.length > 0 ? `
                        <div class="recent-activity">
                            <h3>Recent Error Reports</h3>
                            <ul>
                                ${error_stats.slice(-3).reverse().map(record => `
                                    <li class="error-report">
                                        <span class="activity-date">${new Date(record.timestamp).toLocaleString()}</span>
                                        <span class="activity-details">
                                            <strong>${record.error_type}</strong>: ${record.description}
                                        </span>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            `;

            statsContainer.innerHTML = statsHTML;
        } catch (error) {
            console.error('Error fetching machine stats:', error);
            statsContainer.innerHTML = '<p class="placeholder">Error loading machine statistics</p>';
        }
    }

    // Function to show notifications
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type} fade-in`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Remove notification after 3 seconds
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }

    // Initialize machine select if machines are available
    if (window.machines) {
        populateMachineSelect(window.machines);
    }
}); 