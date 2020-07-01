import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';


@Injectable({
  providedIn: 'root',
})
export class StateService {

  imageID$ = new BehaviorSubject<string|null>(null);
  isLoaderOverlayVisible$ = new BehaviorSubject<boolean>(false);

  constructor() {}

  showImageDetail(imageID: string) {
    this.imageID$.next(imageID);
  }

  turnOffImageDetail() {
    this.imageID$.next(null);
  }

  showLoaderOverlay() {
    this.isLoaderOverlayVisible$.next(true);
  }

  turnOffLoaderOverlay() {
    this.isLoaderOverlayVisible$.next(false);
  }
}
