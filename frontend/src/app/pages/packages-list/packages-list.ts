import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { Package } from '../../models/package.model';
import { PackageService } from '../../services/package.service';

@Component({
  selector: 'app-packages-list',
  imports: [RouterLink],
  templateUrl: './packages-list.html',
  styleUrl: './packages-list.scss',
})
export class PackagesListComponent {
  private readonly packageService = inject(PackageService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly packages = signal<Package[] | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  constructor() {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.packageService
      .getAll()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (packages) => {
          this.packages.set(packages);
          this.loading.set(false);
        },
        error: () => {
          this.error.set('Paketi se nisu mogli učitati. Pokušajte ponovno kasnije.');
          this.loading.set(false);
        },
      });
  }

  protected retry(): void {
    this.load();
  }
}
