document.addEventListener('DOMContentLoaded', () => {
    fetch('/universe_data')
        .then(response => response.json())
        .then(data => {
            renderUniverse(data.nodes, data.edges, data.factions); // Re-enabled passing factions data
        })
        .catch(error => {
            console.error('Error fetching universe data:', error);
        });

    // Tooltip functionality (global, as it's used by universe and system detail)
    const tooltip = d3.select("body").append("div")
        .attr("class", "tooltip");

    function showTooltip(event, d) {
        let resourcesHtml = '';
        if (d.aggregated_resources) {
            resourcesHtml += '<br/><b>Resources:</b><br/>';
            for (const [resource, value] of Object.entries(d.aggregated_resources)) {
                resourcesHtml += `${resource.charAt(0).toUpperCase() + resource.slice(1)}: ${value}<br/>`;
            }
        }
        
        // Re-enabled faction info to tooltip
        let factionHtml = '';
        if (d.factions && Object.keys(d.factions).length > 0) {
            factionHtml += '<br/><b>Factions:</b><br/>';
            for (const factionId in d.factions) {
                const factionState = d.factions[factionId];
                factionHtml += `${factionId}: Inf ${factionState.influence}, Pres ${factionState.presence} ${factionState.controlled_by ? '(Controlled)' : ''}<br/>`;
            }
        }


        tooltip.html(`<b>${d.name} (${d.id})</b><br/>
                      Stability: ${d.stability}<br/>
                      Prosperity: ${d.prosperity}<br/>
                      Planets: ${d.num_planets}
                      ${resourcesHtml}
                      ${factionHtml}`)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 20) + "px")
            .classed("active", true);
    }

    function showLaneTooltip(event, d) {
        tooltip.html(`<b>Lane: ${d.id}</b><br/>
                      From: ${d.source.id}<br/>
                      To: ${d.target.id}<br/>
                      Distance: ${d.distance.toFixed(2)}<br/>
                      Hazard: ${d.hazard.toFixed(2)}`)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 20) + "px")
            .classed("active", true);
    }

    function hideTooltip() {
        tooltip.classed("active", false);
    }

    // Universe visualization function
    function renderUniverse(nodesData, edgesData, factionsData) { // Re-enabled factionsData
        console.log("renderUniverse called. nodesData:", nodesData, "edgesData:", edgesData, "factionsData:", factionsData); // Re-enabled factionsData from log
        const svg = d3.select("#universe-svg");
        
        // Re-enabled factionColors map creation
        const factionColors = new Map();
        if (factionsData) { // Defensive check
            factionsData.forEach(faction => {
                factionColors.set(faction.id, faction.color);
            });
        }
        console.log("Faction colors map:", factionColors);
        
        let width = svg.node().getBoundingClientRect().width;
        let height = svg.node().getBoundingClientRect().height;

        // Set explicit width and height attributes on the SVG element
        svg.attr("width", width).attr("height", height);

        // Create a group for all elements that will be zoomed/panned
        const g_main = svg.append("g");

        // Helper function to draw cluster bubbles (moved outside renderUniverse to be accessible by ticked)
        // This function will be called once the simulation stabilizes
        function drawClusterBubbles(nodes, mainGroup) {
            if (nodes.length === 0) return;

            const k = Math.max(1, Math.round(nodes.length * 0.05)); // 5% ratio for clusters

            // Simple K-means implementation
            let centroids = [];
            for (let i = 0; i < k; i++) {
                centroids.push({
                    x: nodes[Math.floor(Math.random() * nodes.length)].x,
                    y: nodes[Math.floor(Math.random() * nodes.length)].y
                });
            }

            let clusterAssignments = new Array(nodes.length);
            let converged = false;
            let iterations = 0;
            const maxIterations = 100;
            const minChange = 0.1;

            while (!converged && iterations < maxIterations) {
                iterations++;
                converged = true;
                let newCentroids = new Array(k).fill(0).map(() => ({x: 0, y: 0, count: 0}));

                nodes.forEach((node, i) => {
                    let minDist = Infinity;
                    let closestCentroid = -1;
                    centroids.forEach((centroid, j) => {
                        const dist = Math.sqrt(
                            (node.x - centroid.x)**2 + (node.y - centroid.y)**2
                        );
                        if (dist < minDist) {
                            minDist = dist;
                            closestCentroid = j;
                        }
                    });
                    clusterAssignments[i] = closestCentroid;
                    newCentroids[closestCentroid].x += node.x;
                    newCentroids[closestCentroid].y += node.y;
                    newCentroids[closestCentroid].count++;
                });

                centroids.forEach((centroid, i) => {
                    if (newCentroids[i].count > 0) {
                        newCentroids[i].x /= newCentroids[i].count;
                        newCentroids[i].y /= newCentroids[i].count;
                        const change = Math.sqrt(
                            (newCentroids[i].x - centroid.x)**2 + (newCentroids[i].y - centroid.y)**2
                        );
                        if (change > minChange) {
                            converged = false;
                        }
                        centroid.x = newCentroids[i].x;
                        centroid.y = newCentroids[i].y;
                    }
                });
            }

            const clusters = new Array(k).fill(0).map(() => []);
            nodes.forEach((node, i) => {
                if (clusterAssignments[i] !== undefined && clusters[clusterAssignments[i]]) {
                    clusters[clusterAssignments[i]].push(node);
                }
            });

            const hull = d3.polygonHull;
            const clusterColors = d3.scaleOrdinal(d3.schemeCategory10);

            mainGroup.selectAll(".cluster-bubble").remove(); // Remove old bubbles before drawing new ones

            mainGroup.selectAll(".cluster-bubble")
                .data(clusters.filter(c => c.length > 2))
                .enter().insert("path", ":first-child")
                .attr("class", "cluster-bubble")
                .attr("d", d => {
                    const points = d.map(node => [node.x, node.y]);
                    return hull(points) ? `M${hull(points).join("L")}Z` : null;
                })
                .style("fill", (d, i) => clusterColors(i))
                .style("fill-opacity", 0.1)
                .style("stroke", (d, i) => clusterColors(i))
                .style("stroke-width", 2)
                .style("stroke-linejoin", "round");
        }
        // --- End K-means Clustering and Visual Bubbles ---

        // Define zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 10]) // Zoom out to 10%, zoom in to 1000%
            .on("zoom", zoomed);

        svg.call(zoom); // Apply zoom behavior to the SVG

        function zoomed(event) {
            g_main.attr("transform", event.transform);
        }

        // Use D3-force for a force-directed layout
        const simulation = d3.forceSimulation(nodesData)
            .force("link", d3.forceLink(edgesData).id(d => d.id).distance(250)) // Increased link distance
            .force("charge", d3.forceManyBody().strength(-800)) // Increased repulsion strength
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collide", d3.forceCollide(30)) // Prevent nodes from overlapping too much
            .on("tick", ticked);
        
        console.log("D3 Simulation created.");

        // Universe animation state controls
        let universeAnimationState = 'playing'; // 'paused', 'playing'
        // Initial state: start playing
        simulation.alpha(1).restart(); // Start simulation at high alpha to spread nodes

        // Attach event listeners for global controls
        d3.select("#play-button").on("click", () => {
            if (universeAnimationState !== 'playing') {
                universeAnimationState = 'playing';
                simulation.alphaTarget(0.3).restart(); // Resume simulation
                console.log("Universe Simulation: Playing");
            }
        });

        d3.select("#pause-button").on("click", () => {
            if (universeAnimationState !== 'paused') {
                universeAnimationState = 'paused';
                simulation.stop(); // Pause simulation
                console.log("Universe Simulation: Paused");
            }
        });

        d3.select("#reverse-button").on("click", () => {
            // For a force simulation, "reverse" usually means reset or restart
            universeAnimationState = 'playing'; // Resume playing after reset
            simulation.alpha(1).restart(); // Reset and restart simulation with a fresh alpha
            console.log("Universe Simulation: Reset and Playing");
        });

        const link = g_main.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(edgesData)
            .enter().append("line")
            .attr("class", "link")
            .style("stroke", "blue")
            .style("stroke-width", 3)
            .on("mouseover", showLaneTooltip)
            .on("mouseout", hideTooltip);
        console.log("Links appended. Number of Nodes:", link.size()); // Typo fix - from 'log' to 'Logs'

        const node = g_main.append("g")
            .attr("class", "nodes")
            .selectAll("circle")
            .data(nodesData)
            .enter().append("circle")
            .attr("class", "node")
            .attr("r", 15)
            .style("fill", d => { // Re-enabled faction-based color
                let controlledByFactionId = null;

                if (d.factions && Object.keys(d.factions).length > 0) {
                    for (const factionId in d.factions) {
                        const factionState = d.factions[factionId];
                        if (factionState.controlled_by) { // Check if this faction explicitly controls the world
                            controlledByFactionId = factionId;
                            break; // Found the controller, no need to check other factions
                        }
                    }
                }
                
                if (controlledByFactionId && factionColors.has(controlledByFactionId)) {
                    return factionColors.get(controlledByFactionId);
                }
                return "grey"; // Neutral color if no faction controls it
            })
            .style("stroke", "white")
            .style("stroke-width", 2)
            // .call(d3.drag() // Comment out to disable dragging
            //     .on("start", dragstarted)
            //     .on("drag", dragged)
            //     .on("end", dragended))
            .on("mouseover.tooltip", showTooltip)
            .on("mouseout.tooltip", hideTooltip)
            .on("dblclick", showSystemDetail);
        console.log("Nodes appended. Number of Nodes:", node.size()); // Typo fix - from 'log' to 'Logs'

        const label = g_main.append("g")
            .attr("class", "labels")
            .selectAll("text")
            .data(nodesData)
            .enter().append("text")
            .attr("class", "node-label")
            .text(d => d.name)
            .style("fill", "lime");
        console.log("Labels appended. Number of Nodes:", label.size()); // Typo fix - from 'log' to 'Logs'

        function ticked() {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
            
            label
                .attr("x", d => d.x)
                .attr("y", d => d.y - 15); // Position label above the node

            // Check if simulation has stabilized
            if (simulation.alpha() < simulation.alphaMin()) {
                simulation.stop(); // Stop the simulation once it's settled
                console.log("Simulation stabilized. Sending node positions to backend for persistence.");
                sendNodePositionsToBackend(node.data());
                drawClusterBubbles(node.data(), g_main); // Call after stabilization
            }
        }

        function sendNodePositionsToBackend(finalNodes) {
            const nodePositions = {};
            finalNodes.forEach(n => {
                nodePositions[n.id] = { x: n.x, y: n.y };
            });

            fetch('/update_node_positions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ node_positions: nodePositions }),
            })
            .then(response => response.json())
            .then(data => {
                console.log("Backend response to node position update:", data);
            })
            .catch(error => {
                console.error('Error sending node positions to backend:', error);
            });
        }


        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }

        // Resize handler
        window.addEventListener('resize', () => {
            width = svg.node().getBoundingClientRect().width;
            height = svg.node().getBoundingClientRect().height;
            svg.attr("width", width).attr("height", height); // Update SVG attributes on resize too
            simulation.force("center", d3.forceCenter(width / 2, height / 2));
            simulation.alpha(0.3).restart(); // Restart simulation gently
        });
    } // End of renderUniverse function


    // System Detail Modal functionality
    const modal = d3.select("#system-detail-modal");
    const closeButton = d3.select(".close-button");
    const modalSystemName = d3.select("#modal-system-name");
    const modalSystemId = d3.select("#modal-system-id");
    const modalSystemStability = d3.select("#modal-system-stability");
    const modalSystemProsperity = d3.select("#modal-system-prosperity");
    const modalSystemPlanetsCount = d3.select("#modal-system-planets-count");
    const modalAggregatedResources = d3.select("#modal-aggregated-resources");
    const modalDetailedPlanets = d3.select("#modal-detailed-planets");

    function showSystemDetail(event, d) {
        event.stopPropagation(); // Stop propagation to prevent tooltip re-showing or other events

        // Populate modal with system data
        modalSystemName.text(d.name);
        modalSystemId.text(d.id);
        modalSystemStability.text(d.stability);
        modalSystemProsperity.text(d.prosperity);
        modalSystemPlanetsCount.text(d.num_planets);

        // Populate aggregated resources
        let aggResourcesHtml = '<ul>';
        if (d.aggregated_resources) {
            for (const [resource, value] of Object.entries(d.aggregated_resources)) {
                aggResourcesHtml += `<li>${resource.charAt(0).toUpperCase() + resource.slice(1)}: ${value}</li>`;
            }
        } else {
            aggResourcesHtml += '<li>No aggregated resources.</li>';
        }
        aggResourcesHtml += '</ul>';
        modalAggregatedResources.html(aggResourcesHtml);

        // Populate detailed planets
        let detailedPlanetsHtml = '<ul>';
        if (d.detailed_planets && d.detailed_planets.length > 0) {
            d.detailed_planets.forEach(planet => {
                let planetResourcesHtml = '';
                if (planet.resource_potentials) {
                    planetResourcesHtml += ' (Resources: ';
                    planetResourcesHtml += Object.entries(planet.resource_potentials)
                        .map(([res, val]) => `${res.charAt(0).toUpperCase() + res.slice(1)}: ${val}`)
                        .join(', ');
                    planetResourcesHtml += ')';
                }
                detailedPlanetsHtml += `<li>${planet.type.charAt(0).toUpperCase() + planet.type.slice(1)} Planet (Habitability: ${planet.habitability})${planetResourcesHtml}</li>`;
            });
        } else {
            detailedPlanetsHtml += '<li>No detailed planet information available.</li>';
        }
        detailedPlanetsHtml += '</ul>';
        modalDetailedPlanets.html(detailedPlanetsHtml);

        modal.classed("active", true); // Show the modal
        hideTooltip(); // Hide tooltip if it's active

        // Render system visualization AFTER the modal is active to ensure SVG has dimensions
        renderSystemDetailVisualization(d); // Call the new visualization function
    } // Close the showSystemDetail function here

    closeButton.on("click", () => {
        modal.classed("active", false); // Hide the modal
    });

    modal.on("click", (event) => {
        // Hide modal if user clicks outside the modal-content
        if (event.target === modal.node()) {
            modal.classed("active", false);
        }
    });

    function renderSystemDetailVisualization(systemData) {
        const systemSvg = d3.select("#system-visualization-svg");
        systemSvg.selectAll("*").remove(); // Clear previous visualization

        const svgWidth = systemSvg.node().getBoundingClientRect().width;
        const svgHeight = systemSvg.node().getBoundingClientRect().height;

        console.log("System Visualization SVG dimensions:", { width: svgWidth, height: svgHeight });

        const centerX = svgWidth / 2;
        const centerY = svgHeight / 2;

        console.log("System Visualization center:", { centerX: centerX, centerY: centerY });

        // Define a color scale for planet types
        const planetTypeColorScale = d3.scaleOrdinal(d3.schemeCategory10); // Using D3's built-in color scheme

        // Draw the Star
        systemSvg.append("circle")
            .attr("class", "star")
            .attr("cx", centerX)
            .attr("cy", centerY)
            .attr("r", 30 * 0.8); // Star radius scaled down
        
        console.log("Star rendered at:", { cx: centerX, cy: centerY, r: 30 });

        // Draw Planets and Orbits
        if (systemData.detailed_planets && systemData.detailed_planets.length > 0) {
            const maxAllowedOrbitRadius = Math.min(centerX, centerY) * 0.8; // Max space from SVG bounds
            const minOrbitRadius = 45; // Ensure planets are clear of the star (star radius is 30)

            if (systemData.detailed_planets.length === 0) {
                // No planets, nothing to draw or calculate for orbits
                console.log("No detailed planets to render orbits for.");
                return;
            }

            // Space available for spreading planets after the first one (which starts at minOrbitRadius)
            const totalSpreadSpace = Math.max(0, maxAllowedOrbitRadius - minOrbitRadius);
            let orbitStep;

            if (systemData.detailed_planets.length > 1) {
                // Divide the totalSpreadSpace by (numPlanets - 1) to get even steps for remaining planets
                orbitStep = totalSpreadSpace / (systemData.detailed_planets.length - 1);
            } else {
                // If only one planet, orbitStep is effectively 0, it just sits at minOrbitRadius
                orbitStep = 0;
            }

            console.log("Orbit parameters:", { maxAllowedOrbitRadius: maxAllowedOrbitRadius, minOrbitRadius: minOrbitRadius, orbitStep: orbitStep, numPlanets: systemData.detailed_planets.length });

            systemData.detailed_planets.forEach((planet, i) => {
                const orbitRadius = minOrbitRadius + orbitStep * i; // Start from minOrbitRadius
                // No need to Math.min with maxAllowedOrbitRadius here, as orbitStep calculation already ensures it.

                // Draw Orbit
                systemSvg.append("circle")
                    .attr("class", "planet-orbit")
                    .attr("cx", centerX)
                    .attr("cy", centerY)
                    .attr("r", orbitRadius);

                // Position the planet on the orbit (simple static position for now)
                // You could make this dynamic with D3 transitions for animation
                // Randomized angle for initial position
                const angle = Math.random() * 2 * Math.PI; // Full random angle
                const planetX = centerX + orbitRadius * Math.cos(angle);
                const planetY = centerY + orbitRadius * Math.sin(angle);

                // Draw Planet
                systemSvg.append("circle")
                    .attr("class", `planet planet-${i}`) // Add unique class for each planet
                    .attr("cx", planetX) // Apply calculated X position
                    .attr("cy", planetY) // Apply calculated Y position
                    .attr("r", (8 + (planet.habitability * 5)) * 0.8) // Radius based on habitability, scaled down
                    .style("fill", planetTypeColorScale(planet.type)) // Set color based on planet type
                    .on("mouseover", (event) => showPlanetDetailTooltip(event, planet))
                    .on("mouseout", hideTooltip);
                
                console.log(`Planet ${i} final position:`, { cx: planetX, cy: planetY, r: (8 + (planet.habitability * 5)), orbitRadius: orbitRadius, angle: angle });
            });
        }
    } // End of renderSystemDetailVisualization function

    // Dedicated tooltip for planets within the system visualization (optional, can reuse main tooltip)
    // For simplicity, let's reuse the main tooltip for now, but pass different data.
    function showPlanetDetailTooltip(event, planetData) {
        let resourcesHtml = '';
        if (planetData.resource_potentials) {
            resourcesHtml += '<br/><b>Resources:</b><br/>';
            for (const [resource, value] of Object.entries(planetData.resource_potentials)) {
                resourcesHtml += `${resource.charAt(0).toUpperCase() + resource.slice(1)}: ${value}<br/>`;
            }
        }
        tooltip.html(`<b>${planetData.type.charAt(0).toUpperCase() + planetData.type.slice(1)} Planet</b><br/>
                      Habitability: ${planetData.habitability}<br/>
                      ${resourcesHtml}`)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 20) + "px")
            .classed("active", true);
    }
}); // End of DOMContentLoaded event listener