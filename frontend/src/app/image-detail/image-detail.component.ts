import { Component, OnInit, OnDestroy } from '@angular/core';
import { DomSanitizer, SafeStyle } from "@angular/platform-browser";
import { HttpClient } from "@angular/common/http";
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { StateService } from "../state.service";
import { ImageDetailResponse, ImageDetailResponseInterface, Color } from "../types";


@Component({
  selector: "app-image-detail",
  templateUrl: "./image-detail.component.html",
  styleUrls: ["./image-detail.component.scss"]
})
export class ImageDetailComponent implements OnInit {

  imageDetail: ImageDetailResponse | null = null;
  imageID: string | null = null;

  private imageIDSubscription: Subscription;

  constructor(
    private http: HttpClient,
    private state: StateService,
    private sanitizer: DomSanitizer,
    private router: Router
  ) {}

  ngOnInit() {
    this.imageIDSubscription = this.state.imageID$
      .subscribe((imageID: string | null) => {
        this.imageID = imageID;
        if (imageID !== null)
          this.fetchImageDetail();
        else
          this.imageDetail = null;
      })
  }

  ngOnDestroy() {
    this.imageIDSubscription.unsubscribe();
  }

  fetchImageDetail() {
    this.state.showLoaderOverlay();
    const url = `http://localhost:8080/images/${this.imageID}`;
    this.http.get(url).subscribe(
      (response) => {
        this.state.turnOffLoaderOverlay();
        this.imageDetail = new ImageDetailResponse(<ImageDetailResponseInterface>response);
      },
      (error) => {
        this.state.turnOffLoaderOverlay();
        console.log(error);
      }
    );
  }

  getBackgroundURL(): SafeStyle {
    if (this.imageDetail === null)
      throw new Error('imageDetail must be defined');
    return this.sanitizer.bypassSecurityTrustStyle(
      `url(${this.imageDetail.image.url_big})`
    );
  }

  close() {
    this.state.turnOffImageDetail();
  }

  showImageList(color: Color) {
    this.router.navigateByUrl(`/images/${color.toHex()}`);
    this.close();
  }
}
