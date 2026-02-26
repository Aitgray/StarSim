// Define specific border colors for planet types
const planetBorderColors = {
    "continental": "#228B22",
    "ocean": "#000080",
    "arid": "#FF8C00",
    "desert": "#C2B280",

    "airless": "#FFFFFF",
    "ash": "#A9A9A9",
    "toxic": "#006400",
    "molten": "#cf1020",
    "barren": "#000000",
    "barren cold": "#00008B",
    "volcanic": "#FFA500",
    "ice": "#00f7ff",

    "ice giant": "#00f7ff",
    "helium giant": "#800000",
    "gas giant": "#FF8C00"
};

document.addEventListener('DOMContentLoaded', () => {
    let universeFactionsData;
    let universeNodesData;
    let universeEdgesData;
    let universeRender;
    let simPollHandle = null;

    function postJson(url, payload) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload || {}),
        }).then(response => response.json());
    }

    function updateTick(meta) {
        const tickEl = document.getElementById("sim-tick");
        if (!tickEl) return;
        const tickVal = meta && typeof meta.tick === "number" ? meta.tick : 0;
        tickEl.textContent = `Tick: ${tickVal}`;
    }

    function applySimState(data) {
        if (!data) return;
        updateTick(data.meta);

        if (!universeRender) {
            universeFactionsData = data.factions;
            universeNodesData = data.nodes;
            universeEdgesData = data.edges;
            universeRender = renderUniverse(universeNodesData, universeEdgesData, universeFactionsData);
            return;
        }

        if (!universeNodesData || data.nodes.length !== universeNodesData.length) {
            console.warn("Universe node count changed; reload required to re-render.");
            return;
        }

        const incomingById = new Map(data.nodes.map(n => [n.id, n]));
        universeNodesData.forEach(node => {
            const updated = incomingById.get(node.id);
            if (updated) {
                Object.assign(node, updated);
            }
        });

        if (universeRender && universeRender.refresh) {
            universeRender.refresh();
        }
    }

    function fetchSimState() {
        return fetch('/sim/state')
            .then(response => response.json())
            .then(data => {
                applySimState(data);
                return data;
            })
            .catch(error => {
                console.error('Error fetching sim state:', error);
            });
    }

    fetchSimState().then(() => {
        if (!simPollHandle) {
            simPollHandle = setInterval(fetchSimState, 1000);
        }
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

    // Helper function to lighten a hex color by a given percentage
    function lightenColor(hex, percent) {
        let f = parseInt(hex.slice(1), 16),
            t = percent < 0 ? 0 : 255,
            p = percent < 0 ? percent * -1 : percent,
            c = (f & 0x00FF00) >> 8,
            c1 = (f & 0x0000FF),
            c2 = (f & 0xFF0000) >> 16;
        return "#" + (
            0x1000000 +
            (Math.round((t - c2) * p) + c2) * 0x10000 +
            (Math.round((t - c) * p) + c) * 0x100 +
            (Math.round((t - c1) * p) + c1)
        ).toString(16).slice(1);
    }

    // Function to determine border color based on habitability
    function getHabitableBorderColor(planet) {
        // Assuming habitability > 0.1 means habitable for border coloring purposes
        return planet.habitability > 0.1 ? "green" : "grey";
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
        renderFactionKey(factionsData); // Call the new function here
        
        let width = svg.node().getBoundingClientRect().width;
        let height = svg.node().getBoundingClientRect().height;

        // Set explicit width and height attributes on the SVG element
        svg.attr("width", width).attr("height", height);

        // Create a group for all elements that will be zoomed/panned
        const g_main = svg.append("g");

        // Helper function to draw cluster bubbles (moved outside renderUniverse to be accessible by ticked)
        // This function will be called once the simulation stabilizes
        function drawClusterBubbles(nodes, mainGroup) {
            let sectorKeyData = []; // Declare sectorKeyData here
            if (nodes.length === 0) return sectorKeyData; // Return empty if no nodes

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
            const line = d3.line().curve(d3.curveCatmullRom.alpha(0.5)); // Define a line generator with Catmull-Rom curve
            const clusterColors = d3.scaleOrdinal(d3.schemeCategory10);

            mainGroup.selectAll(".cluster-bubble").remove(); // Remove old bubbles before drawing new ones

            mainGroup.selectAll(".cluster-bubble")
                .data(clusters.filter(c => c.length > 2))
                .enter().insert("path", ":first-child")
                .attr("class", "cluster-bubble")
                .attr("d", d => {
                    const points = d.map(node => [node.x, node.y]);
                    // If hull returns points, use the line generator to draw a smoothed path
                    // Also, add the closing 'Z' to ensure it's a closed path
                    return hull(points) ? line(hull(points)) + "Z" : null;
                })
                .style("fill", (d, i) => {
                    const color = clusterColors(i);
                    const name = `Sector ${i + 1}`; // Simple naming
                    sectorKeyData.push({ id: `sector-${i}`, name: name, color: color });
                    return color;
                })
                .style("fill-opacity", 0.1)
                .style("stroke", (d, i) => clusterColors(i))
                .style("stroke-width", 2)
                .style("stroke-linejoin", "round");
            
            // Return the data for the key
            return sectorKeyData;
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

        // Initial state: start playing
        simulation.alpha(1).restart(); // Start simulation at high alpha to spread nodes

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

        function getNodeColor(d) {
            let controlledByFactionId = null;

            if (d.factions && Object.keys(d.factions).length > 0) {
                for (const factionId in d.factions) {
                    const factionState = d.factions[factionId];
                    if (factionState.controlled_by) {
                        controlledByFactionId = factionId;
                        break;
                    }
                }
            }

            if (controlledByFactionId && factionColors.has(controlledByFactionId)) {
                return factionColors.get(controlledByFactionId);
            }
            return "grey";
        }

        const node = g_main.append("g")
            .attr("class", "nodes")
            .selectAll("circle")
            .data(nodesData)
            .enter().append("circle")
            .attr("class", "node")
            .attr("r", 15)
            .style("fill", d => getNodeColor(d))
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
                const sectorData = drawClusterBubbles(node.data(), g_main); // Capture the returned data
                renderSectorKey(sectorData); // Call new function to render sector key
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

        function refresh() {
            node.style("fill", d => getNodeColor(d));
            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
            label
                .attr("x", d => d.x)
                .attr("y", d => d.y - 15);
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
        }

        // Attach event listeners for sim controls (once)
        d3.select("#play-button").on("click", () => {
            postJson('/sim/play');
        });

        d3.select("#pause-button").on("click", () => {
            postJson('/sim/pause');
        });

        d3.select("#step-button").on("click", () => {
            postJson('/sim/step', { steps: 1 }).then(fetchSimState);
        });

        d3.select("#rewind-button").on("click", () => {
            postJson('/sim/rewind', { steps: 1 }).then(fetchSimState);
        });

        return { refresh };
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

        // Populate faction evaluations
        const modalFactionEvaluations = d3.select("#modal-faction-evaluations");
        let factionEvaluationsHtml = '<ul>';
        if (d.faction_evaluations && universeFactionsData) {
            // Create a map for quick lookup of faction names by ID
            const factionNameMap = new Map(universeFactionsData.map(f => [f.id, f.name]));
            for (const [factionId, evaluation] of Object.entries(d.faction_evaluations)) {
                const factionName = factionNameMap.get(factionId) || factionId; // Fallback to ID if name not found
                factionEvaluationsHtml += `<li>${factionName}: ${evaluation.toFixed(2)}</li>`;
            }
        } else {
            factionEvaluationsHtml += '<li>No faction evaluation data.</li>';
        }
        factionEvaluationsHtml += '</ul>';
        modalFactionEvaluations.html(factionEvaluationsHtml);

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
                if (planet.resource_potentials && Object.keys(planet.resource_potentials).length > 0) {
                    planetResourcesHtml = Object.entries(planet.resource_potentials)
                        .map(([res, val]) => `${res.charAt(0).toUpperCase() + res.slice(1)}: ${val}`)
                        .join(', ');
                }
                detailedPlanetsHtml += `<li>
                                        <b>Planet name: ${planet.name}</b><br/>
                                        Planet type: ${planet.type.charAt(0).toUpperCase() + planet.type.slice(1)}<br/>
                                        Habitability: ${planet.habitability}<br/>
                                        Resources: ${planetResourcesHtml || 'None'}
                                    </li>`;
            });
        } else {
            detailedPlanetsHtml += '<li>No detailed planet information available.</li>';
        }
        detailedPlanetsHtml += '</ul>';
        modalDetailedPlanets.html(detailedPlanetsHtml);

        modal.classed("active", true); // Show the modal
        hideTooltip(); // Hide tooltip if it's active

        renderPlanetKey(planetBorderColors); // Call to render the planet key

        // Render system visualization AFTER the modal is active to ensure SVG has dimensions
        renderSystemDetailVisualization(d, d.is_capital); // Pass the is_capital flag
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

    function renderSystemDetailVisualization(systemData, isCapitalSystem = false) { // Add isCapitalSystem parameter
        const systemSvg = d3.select("#system-visualization-svg");
        systemSvg.selectAll("*").remove(); // Clear previous visualization

        const svgWidth = systemSvg.node().getBoundingClientRect().width;
        const svgHeight = systemSvg.node().getBoundingClientRect().height;

        console.log("System Visualization SVG dimensions:", { width: svgWidth, height: svgHeight });

        const centerX = svgWidth / 2;
        const centerY = svgHeight / 2;

        console.log("System Visualization center:", { centerX: centerX, centerY: centerY });

        // Define a color scale for planet types
        // const planetTypeColorScale = d3.scaleOrdinal(d3.schemeCategory10); // Using D3's built-in color scheme



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
                    .style("fill", d => planetBorderColors[planet.type] || "#808080") // Fill color based on planet type, fallback to grey
                    .style("stroke", d => getHabitableBorderColor(planet)) // Border color based on habitability
                    .style("stroke-width", 3)
                    .attr("stroke-dasharray", (isCapitalSystem && planet.name === systemData.capital_planet_name) ? "5,5" : "none") // Dashed border only for the specific capital planet // Increase border width for visibility
                    .on("mouseover", (event) => showPlanetDetailTooltip(event, planet))
                    .on("mouseout", hideTooltip);
                
                console.log(`Planet ${i} final position:`, { cx: planetX, cy: centerY, r: (8 + (planet.habitability * 5)), orbitRadius: orbitRadius, angle: angle });
            });
        }
    } // End of renderSystemDetailVisualization function

    // Dedicated tooltip for planets within the system visualization (optional, can reuse main tooltip)
    // For simplicity, let's reuse the main tooltip for now, but pass different data.
    function showPlanetDetailTooltip(event, planetData) {
        let resourcesListHtml = '';
        if (planetData.resource_potentials) {
            resourcesListHtml = Object.entries(planetData.resource_potentials)
                .map(([resource, value]) => `${resource.charAt(0).toUpperCase() + resource.slice(1)}: ${value}`)
                .join(', ');
        }
        tooltip.html(`<b>Planet name: ${planetData.name}</b><br/>
                      Planet type: ${planetData.type.charAt(0).toUpperCase() + planetData.type.slice(1)}<br/>
                      Habitability: ${planetData.habitability}<br/>
                      Resources: ${resourcesListHtml || 'None'}`)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 20) + "px")
            .classed("active", true);
    }

    function renderFactionKey(factionsData) {
        const keyContainer = d3.select("#faction-key");
        keyContainer.html(''); // Clear previous key

        keyContainer.append("h3").text("Factions");

        const factionItems = keyContainer.selectAll(".faction-item")
            .data(factionsData)
            .enter().append("div")
            .attr("class", "faction-item");

        factionItems.append("div")
            .attr("class", "faction-color-box")
            .style("background-color", d => d.color);

        factionItems.append("span")
            .attr("class", "faction-name")
            .text(d => d.name);
    }

    // Function to render the sector key
    function renderSectorKey(sectorData) {
        const keyContainer = d3.select("#sector-key"); // Assuming #sector-key container in HTML
        keyContainer.html(''); // Clear previous key

        keyContainer.append("h3").text("Sectors");

        const sectorItems = keyContainer.selectAll(".sector-item")
            .data(sectorData)
            .enter().append("div")
            .attr("class", "sector-item");

        sectorItems.append("div")
            .attr("class", "sector-color-box")
            .style("background-color", d => d.color);

        sectorItems.append("span")
            .attr("class", "sector-name")
            .text(d => d.name);
    }

    // Function to render the planet type key
    function renderPlanetKey(planetBorderColorsMap) {
        const keyContainer = d3.select("#planet-key-modal");
        keyContainer.html(''); // Clear previous key

        const planetTypes = Object.keys(planetBorderColorsMap).sort(); // Sort for consistent order

        planetTypes.forEach(type => {
            const color = planetBorderColorsMap[type];
            const item = keyContainer.append("div")
                .attr("class", "planet-key-item");

            item.append("div")
                .attr("class", "planet-key-color-box")
                .style("background-color", color)
                .style("border", `1px solid ${color}`); // Border of the same color

            item.append("span")
                .attr("class", "planet-key-name")
                .text(type.charAt(0).toUpperCase() + type.slice(1)); // Capitalize first letter
        });
    }
}); // End of DOMContentLoaded event listener
