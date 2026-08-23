package com.routemind.business.api.reconciliation;

import com.routemind.business.application.reconciliation.ReconciliationReport;
import com.routemind.business.application.reconciliation.ReconciliationService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/reliability/reconciliation")
@CrossOrigin(origins = { "http://localhost:4173", "http://127.0.0.1:4173" })
public class ReconciliationController {

	private final ReconciliationService service;

	public ReconciliationController(ReconciliationService service) {
		this.service = service;
	}

	@GetMapping
	public ResponseEntity<ReconciliationReport> latest() {
		return service.latest().map(ResponseEntity::ok).orElseGet(() -> ResponseEntity.notFound().build());
	}

	@PostMapping("/checks")
	public ReconciliationReport check() {
		return service.runDetectOnly();
	}
}
