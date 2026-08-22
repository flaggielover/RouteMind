package com.routemind.business.infrastructure.persistence.outbox;

import com.routemind.business.domain.outbox.OutboxStatus;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataOutboxRepository extends JpaRepository<OutboxEntity, UUID> {

	@Lock(LockModeType.PESSIMISTIC_WRITE)
	List<OutboxEntity> findByStatusInAndNextAttemptAtLessThanEqualOrderByCreatedAtAsc(
			List<OutboxStatus> statuses, Instant now, Pageable pageable);

	List<OutboxEntity> findByOrderByCreatedAtDescEventIdDesc(Pageable pageable);
}
